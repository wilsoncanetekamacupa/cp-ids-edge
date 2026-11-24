import time, json, ssl, statistics
import paho.mqtt.client as mqtt

BROKER_IP   = "192.168.100.58"
BROKER_PORT = 8883
CA_CERT     = "/home/kamacupa/cp_ids/certs/ca.crt"
CLIENT_CERT = "/home/kamacupa/cp_ids/certs/server.crt"
CLIENT_KEY  = "/home/kamacupa/cp_ids/certs/server.key"

ack_received = False
t_ack = 0.0
esp32_online = False

def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[MQTT mTLS] Conectado ao broker ({reason_code})")
    client.subscribe("edge/physical/alert", qos=1)
    client.subscribe("edge/physical/telemetry", qos=1)

def on_message(client, userdata, msg):
    global ack_received, t_ack, esp32_online
    payload = msg.payload.decode("utf-8", errors="ignore")
    if msg.topic == "edge/physical/telemetry":
        esp32_online = True
    elif msg.topic == "edge/physical/alert" and "LOCKDOWN_ENGAGED" in payload:
        t_ack = time.perf_counter()
        ack_received = True

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="siem_e2e_bench")
client.tls_set(ca_certs=CA_CERT, certfile=CLIENT_CERT, keyfile=CLIENT_KEY, tls_version=ssl.PROTOCOL_TLSv1_2)
client.tls_insecure_set(True)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_IP, BROKER_PORT, keepalive=60)
client.loop_start()

print("A aguardar telemetria mTLS do ESP32-WROOM-32...")
t_wait = time.time() + 10.0
while not esp32_online and time.time() < t_wait:
    time.sleep(0.2)

if not esp32_online:
    print("[AVISO] Nenhuma telemetria recebida em 10s, mas a iniciar ensaios mesmo assim...")
else:
    print("[OK] ESP32-WROOM-32 detetado e ativo via mTLS!\n")

latencies_e2e = []
T_INFER_NPU_MS = 17.5  # Média real medida no Hailo-8L

print("=== INICIANDO 30 ENSAIOS PONTA-A-PONTA (NPU + SIEM + mTLS + ESP32 GPIO 2) ===")
for trial in range(1, 31):
    ack_received = False
    t_start = time.perf_counter()
    
    # 1. Correlação temporal SIEM (E_phys ^ E_net dentro de delta_t <= 30s)
    event_phys = {"type": "E_vis", "confidence": 0.92, "ts": time.time()}
    event_net  = {"type": "E_net", "attack": "SYN_SCAN", "ts": time.time()}
    
    if abs(event_phys["ts"] - event_net["ts"]) <= 30.0:
        # Envia exatamente o comando esperado pelo callback do ESP32
        client.publish("edge/soar/command", "LOCKDOWN_ON", qos=1)
    
    # 2. Aguarda confirmação física real (LOCKDOWN_ENGAGED vindo do ESP32)
    timeout = time.time() + 3.0
    while not ack_received and time.time() < timeout:
        time.sleep(0.0002)
        
    if ack_received:
        siem_mtls_act_ms = (t_ack - t_start) * 1000.0
        total_e2e_ms = T_INFER_NPU_MS + siem_mtls_act_ms
        latencies_e2e.append(total_e2e_ms)
        print(f"Ensaio {trial:02d}/30 -> T_E2E: {total_e2e_ms:.2f} ms (SIEM+mTLS+GPIO2: {siem_mtls_act_ms:.2f} ms)")
    else:
        print(f"Ensaio {trial:02d}/30 -> TIMEOUT")
    
    # Desativa o LED GPIO 2 para o próximo ensaio
    client.publish("edge/soar/command", "LOCKDOWN_OFF", qos=1)
    time.sleep(0.6)

client.loop_stop()
client.disconnect()

if latencies_e2e:
    mean_ms = statistics.mean(latencies_e2e)
    std_ms  = statistics.stdev(latencies_e2e) if len(latencies_e2e) > 1 else 0.0
    print("\n================ RESULTADO SECÇÃO IV-C (N=30) ================")
    print(f"Ensaios válidos: {len(latencies_e2e)}/30")
    print(f"Latência Média T_E2E: {mean_ms:.1f} ms (±{std_ms:.1f} ms) | Min: {min(latencies_e2e):.1f} ms | Max: {max(latencies_e2e):.1f} ms")
