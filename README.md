# CP-IDS: Near-Edge Cyber-Physical Intrusion Detection

Official artifact repository for the IEEE paper:
**"Near-Edge Cyber-Physical Intrusion Detection: Correlating NPU-Accelerated Vision, mTLS-Authenticated Telemetry, and Network Events"**

## Architecture Overview
1. **Edge Sensing & Actuation:** Raspberry Pi AI Camera (Sony IMX500 CSI) + ESP32-WROOM-32 (DHT11, MQ-135, GPIO 2 containment indicator).
2. **Edge AI & Fast Correlation Gateway:** Raspberry Pi 5 (8GB) + Hailo-8L NPU (13 TOPS, quantized INT8 `yolov8s_h8l.hef`), OpenCV Laplacian tamper detector, Eclipse Mosquitto (X.509 mTLS on port `8883`), and fast in-memory JSON containment evaluator.
3. **Near-Edge SIEM Auditing:** Wazuh SIEM manager (`v4.11`) for persistent log indexing and Tier 2 operator alerting.

## Repository Structure
- `benchmark_e7_multithread_cpu.py`: 4-thread FP32 OpenCV-DNN CPU vs. Hailo-8L INT8 NPU latency, core load, thermal, and PMIC power benchmark.
- `measure_e6_n1000.py`: Hybrid measured/modeled end-to-end containment latency evaluation ($N = 1000$ trials).
- `evaluate_v3_reconciled.py`: Stratified train/held-out policy simulation ($N = 500$, seed `42`), per-group confusion matrices (`G1`–`G5`), McNemar exact test, and $\Delta t$ sensitivity sweep.
- `configs/mosquitto_mtls.conf`: Eclipse Mosquitto X.509 mutual-TLS broker template.
- `configs/wazuh_cpids_rules.xml`: Custom Wazuh SIEM correlation and auditing rules.

## Reproducibility
All policy simulation experiments use deterministic seeds (`random.seed(42)` and `np.random.default_rng(42)`).
