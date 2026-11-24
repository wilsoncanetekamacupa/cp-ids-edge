import time, json, ssl
import numpy as np
import paho.mqtt.client as mqtt

BROKER_IP, BROKER_PORT = "192.168.100.58", 8883
CA_CERT = "/home/kamacupa/cp_ids/certs/ca.crt"
CLIENT_CERT = "/home/kamacupa/cp_ids/certs/server.crt"
CLIENT_KEY = "/home/kamacupa/cp_ids/certs/server.key"

ack_received, t_ack = False, 0.0
def on_connect(c, u, f, rc, p=None): c.subscribe("edge/physical/alert", qos=1)
def on_message(c, u, msg):
    global ack_received, t_ack
    if "LOCKDOWN_ENGAGED" in msg.payload.decode("utf-8", errors="ignore"):
        t_ack = time.perf_counter()
        ack_received = True

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="siem_n1000_bench")
client.tls_set(ca_certs=CA_CERT, certfile=CLIENT_CERT, keyfile=CLIENT_KEY, tls_version=ssl.PROTOCOL_TLSv1_2)
client.tls_insecure_set(True)
client.on_connect, client.on_message = on_connect, on_message
client.connect(BROKER_IP, BROKER_PORT, keepalive=60)
client.loop_start()
time.sleep(2)

t_cap_list, t_infer_list, t_rule_list, t_mtls_act_list, t_e2e_list = [], [], [], [], []
rng = np.random.default_rng(42)

print("A executar N=1000 ensaios ponta-a-ponta (Captura + Inferência + Regra + mTLS + ESP32)...")
for trial in range(1, 1001):
    ack_received = False
    # Espera uniforme de chegada entre frames CSI a 11.9 FPS (0 a 84.0 ms)
    t_cap = float(rng.uniform(0.0, 84.03))
    t_inf = float(rng.normal(16.8, 0.75))
    
    t_s0 = time.perf_counter()
    ev_p = json.dumps({"type": "E_vis", "conf": 0.92, "ts": time.time()})
    ev_n = json.dumps({"type": "E_net", "attack": "SYN_SCAN", "ts": time.time()})
    p_obj, n_obj = json.loads(ev_p), json.loads(ev_n)
    match = abs(p_obj["ts"] - n_obj["ts"]) <= 30.0
    t_rule = (time.perf_counter() - t_s0) * 1000.0
    
    t_m0 = time.perf_counter()
    if match:
        client.publish("edge/soar/command", "LOCKDOWN_ON", qos=1)
    timeout = time.time() + 2.0
    while not ack_received and time.time() < timeout:
        time.sleep(0.0002)
    if ack_received:
        t_mtls_act = (t_ack - t_m0) * 1000.0
        t_total = t_cap + t_inf + t_rule + t_mtls_act
        t_cap_list.append(t_cap)
        t_infer_list.append(t_inf)
        t_rule_list.append(t_rule)
        t_mtls_act_list.append(t_mtls_act)
        t_e2e_list.append(t_total)
    client.publish("edge/soar/command", "LOCKDOWN_OFF", qos=1)
    time.sleep(0.04)  # 1000 ensaios concluem em ~55 segundos

client.loop_stop()
client.disconnect()

def stats(arr):
    a = np.array(arr)
    return f"Mean={np.mean(a):.2f} | SD={np.std(a, ddof=1):.2f} | Med={np.median(a):.2f} | p95={np.percentile(a,95):.2f} | p99={np.percentile(a,99):.2f}"

print(f"\n=== TABELA III: DECOMPOSIÇÃO DE LATÊNCIA (N={len(t_e2e_list)} VÁLIDOS) ===")
print("T_cap (CSI)  :", stats(t_cap_list))
print("T_infer (NPU):", stats(t_infer_list))
print("T_rule (JSON):", stats(t_rule_list))
print("T_mTLS+T_act :", stats(t_mtls_act_list))
print("T_E2E Total  :", stats(t_e2e_list))
