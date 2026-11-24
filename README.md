# CP-IDS: Near-Edge Cyber-Physical Intrusion Detection

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%205%20%7C%20Hailo--8L%20%7C%20ESP32-green.svg)]()
[![SIEM](https://img.shields.io/badge/SIEM-Wazuh%20v4.11-orange.svg)]()

Official artifact repository for the IEEE paper:
**"Near-Edge Cyber-Physical Intrusion Detection: Correlating NPU-Accelerated Vision, mTLS-Authenticated Telemetry, and Network Events"**

**Author:** Wilson Canete Kamacupa  
**Affiliation:** MSc. Computer Science Engineering — Independent Security Researcher / University of Debrecen Alumni (Benguela, Angola)  
**Contact:** wilsoncanetekamacupa@gmail.com  

---

## Architecture Overview

CP-IDS separates a fast in-memory containment path from persistent SIEM auditing across four modular layers:

1. **Edge Sensing & Actuation Layer:** Raspberry Pi AI Camera (Sony IMX500 CSI sensor) + ESP32-WROOM-32 node (DHT11 temperature/humidity on `GPIO 23`, MQ-135 gas sensor on `GPIO 34`, and `GPIO 2` containment indicator).
2. **Edge AI & Fast Correlation Gateway:** Raspberry Pi 5 (8GB RAM) + Hailo-8L NPU (13 TOPS, quantized INT8 `yolov8s_h8l.hef`), OpenCV Laplacian sharpness tamper detector, Eclipse Mosquitto broker enforcing X.509 mutual TLS (port `8883`), and a low-latency in-memory JSON containment evaluator.
3. **Near-Edge SIEM Auditing Layer:** Wazuh SIEM manager (`v4.11`) for persistent log indexing, compliance auditing, and Tier 2 operator alert management.
4. **Automated Response Layer (SOAR/IRS):** Authenticated `LOCKDOWN_ON` command delivery over mTLS MQTT to trigger containment signaling on the ESP32.

---

## Key Empirical Highlights

* **NPU Offloading:** Per-frame inference latency reduced by **71.4%** (`58.8 ms` on 4-thread FP32 OpenCV-DNN CPU vs. `16.8 ms` on Hailo-8L INT8 NPU), lowering peak single-core CPU load from `97.8%` to `22.7%`.
* **Containment Signaling Latency ($N = 1000$ trials):** Median end-to-end latency of **`113.2 ms`** (mean `127.2 ms`, $p_{95}$ `241.2 ms`).
* **Tiered Policy Separation ($N = 500$ scripted trials, $250$ held out):**
  * **Tier 1 Automated Containment ($\theta_1 = 0.65$):** `98.0%` precision, `0.7%` overall FPR (`2.0%` on coincident benign trials `G4`).
  * **Tier 1 + Tier 2 Any-Alert Policy ($\theta_2 = 0.80$):** `98.0%` recall (`95% CI: 93.0–99.8%`), `9.3%` FPR, and `92.5%` F1-score.

---

## Repository Structure

```text
cp-ids-edge/
├── benchmark_e7_multithread_cpu.py   # 4-thread CPU vs. Hailo-8L NPU latency, core load, temp & PMIC power
├── measure_e6_n1000.py               # Hybrid measured/modeled end-to-end latency evaluation (N=1000)
├── evaluate_v3_reconciled.py         # Stratified train/held-out policy simulation (N=500) & McNemar test
├── configs/
│   ├── mosquitto_mtls.conf           # Eclipse Mosquitto X.509 mTLS broker template
│   └── wazuh_cpids_rules.xml         # Custom Wazuh SIEM correlation and auditing rules
├── LICENSE                           # MIT License
└── README.md                         # Artifact documentation

# 1. Run stratified policy simulation, per-group confusion matrices (G1-G5), and McNemar test
python3 evaluate_v3_reconciled.py

# 2. Run 4-thread CPU hardware baseline benchmark (60s continuous run)
python3 benchmark_e7_multithread_cpu.py

# 3. Run N=1000 hybrid measured/modeled containment latency benchmark (requires live mTLS broker & ESP32)
python3 measure_e6_n1000.py
