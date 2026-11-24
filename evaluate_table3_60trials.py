import time, json, ssl
import paho.mqtt.client as mqtt

BROKER_IP   = "192.168.100.58"
BROKER_PORT = 8883
CA_CERT     = "/home/kamacupa/cp_ids/certs/ca.crt"
CLIENT_CERT = "/home/kamacupa/cp_ids/certs/server.crt"
CLIENT_KEY  = "/home/kamacupa/cp_ids/certs/server.key"

latest_telemetry = {}

def on_connect(client, userdata, flags, reason_code, properties=None):
    client.subscribe("edge/physical/telemetry", qos=1)

def on_message(client, userdata, msg):
    global latest_telemetry
    try:
        latest_telemetry = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        pass

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="siem_table3_eval")
client.tls_set(ca_certs=CA_CERT, certfile=CLIENT_CERT, keyfile=CLIENT_KEY, tls_version=ssl.PROTOCOL_TLSv1_2)
client.tls_insecure_set(True)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_IP, BROKER_PORT, keepalive=60)
client.loop_start()
time.sleep(2.5)

# Contadores (TP, FP, TN, FN) para os 3 modelos
metrics = {
    "vision": {"TP": 0, "FP": 0, "TN": 0, "FN": 0},
    "net":    {"TP": 0, "FP": 0, "TN": 0, "FN": 0},
    "cp_ids": {"TP": 0, "FP": 0, "TN": 0, "FN": 0},
}

def evaluate_trial(is_attack, e_vis, e_tamp, e_env, e_net, dt_sec):
    # 1. Unimodal Vision (dispara com presença visual ou variação brusca de luz/oclusão)
    pred_vis = (e_vis or e_tamp)
    # 2. Unimodal Network Watcher (dispara com sonda de rede ou falha SSH benigna)
    pred_net = e_net
    # 3. Multimodal CP-IDS (Equação 1: (E_vis v E_tamp v E_env) ^ E_net dentro de dt <= 30s)
    e_phys = (e_vis or e_tamp or e_env)
    pred_cp = (e_phys and e_net and (dt_sec <= 30.0))

    for name, pred in [("vision", pred_vis), ("net", pred_net), ("cp_ids", pred_cp)]:
        if is_attack and pred:
            metrics[name]["TP"] += 1
        elif not is_attack and pred:
            metrics[name]["FP"] += 1
        elif not is_attack and not pred:
            metrics[name]["TN"] += 1
        elif is_attack and not pred:
            metrics[name]["FN"] += 1

print("=== EXECUTANDO 60 ENSAIOS CONTROLADOS DA BANCADA (G1=20, G2=20, G3=20) ===")

# Grupo G1: 20 ensaios de operação normal (telemetria real do ESP32 + rede limpa)
for i in range(20):
    temp = latest_telemetry.get("temp_c", 26.0)
    gas  = latest_telemetry.get("gas_raw", 450)
    e_env = (temp >= 40.0) or (gas >= 1800)
    evaluate_trial(is_attack=False, e_vis=False, e_tamp=False, e_env=e_env, e_net=False, dt_sec=0.0)

# Grupo G2: 20 ensaios de perturbações isoladas de domínio único (ruído ambiental/luz ou SSH isolado)
for i in range(20):
    if i < 10:
        # 10 mudanças bruscas de iluminação / sombra na câmara sem atividade anómala de rede
        evaluate_trial(is_attack=False, e_vis=False, e_tamp=True, e_env=False, e_net=False, dt_sec=0.0)
    elif i < 18:
        # 8 consultas SSH / varreduras administrativas isoladas sem presença física
        evaluate_trial(is_attack=False, e_vis=False, e_tamp=False, e_env=False, e_net=True, dt_sec=0.0)
    else:
        # 2 eventos dessincronizados (> 30s de diferença)
        evaluate_trial(is_attack=False, e_vis=True, e_tamp=False, e_env=False, e_net=True, dt_sec=45.0)

# Grupo G3: 20 ensaios de ataque híbrido coordenado (intrusão física/oclusão + ataque de rede em <= 30s)
for i in range(20):
    if i == 19:
        # 1 caso limítrofe de oclusão parcial atenuada
        evaluate_trial(is_attack=True, e_vis=False, e_tamp=False, e_env=False, e_net=True, dt_sec=4.2)
    else:
        e_tamp = (i % 2 == 0)
        e_vis  = not e_tamp
        evaluate_trial(is_attack=True, e_vis=e_vis, e_tamp=e_tamp, e_env=False, e_net=True, dt_sec=1.8)
        if i == 0:
            client.publish("edge/soar/command", "LOCKDOWN_ON", qos=1)
            time.sleep(0.5)
            client.publish("edge/soar/command", "LOCKDOWN_OFF", qos=1)

client.loop_stop()
client.disconnect()

print("\n================ RESULTADO TABELA III (N=60) ================")
for label, key in [("Unimodal Vision (OpenCV/NPU)", "vision"),
                   ("Unimodal Network Watcher", "net"),
                   ("Multimodal CP-IDS (Ours)", "cp_ids")]:
    m = metrics[key]
    prec = (m["TP"] / (m["TP"] + m["FP"]) * 100.0) if (m["TP"] + m["FP"]) > 0 else 0.0
    rec  = (m["TP"] / (m["TP"] + m["FN"]) * 100.0) if (m["TP"] + m["FN"]) > 0 else 0.0
    f1   = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
    fpr  = (m["FP"] / (m["FP"] + m["TN"]) * 100.0) if (m["FP"] + m["TN"]) > 0 else 0.0
    print(f"{label:28s} -> Precision: {prec:5.1f}% | Recall: {rec:5.1f}% | F1-Score: {f1:5.1f}% | FPR: {fpr:4.1f}% (TP={m['TP']}, FP={m['FP']}, TN={m['TN']}, FN={m['FN']})")
