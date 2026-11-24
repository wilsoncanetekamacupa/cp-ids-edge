import time, subprocess, re, statistics, psutil, cv2
import numpy as np
from picamera2 import Picamera2

def get_temp():
    out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True)
    return float(re.search(r"temp=([\d\.]+)", out).group(1))

def get_power_w():
    try:
        out = subprocess.check_output(["vcgencmd", "pmic_read_adc"], text=True)
        volts = dict(re.findall(r"(\S+)_V volt\(\d+\)=([\d\.]+)V", out))
        amps  = dict(re.findall(r"(\S+)_A current\(\d+\)=([\d\.]+)A", out))
        total_w = sum(float(volts[k]) * float(amps[k]) for k in volts if k in amps)
        return total_w
    except Exception:
        return 0.0

def measure_system(duration=60, workload_fn=None):
    psutil.cpu_percent(interval=None, percpu=True)
    cpu_all, cpu_max_core, temps, powers, latencies = [], [], [], [], []
    t_start = time.time()
    t_sample = t_start
    while time.time() - t_start < duration:
        t0 = time.perf_counter()
        if workload_fn:
            workload_fn()
        latencies.append((time.perf_counter() - t0) * 1000.0)
        if time.time() - t_sample >= 1.0:
            cores = psutil.cpu_percent(interval=None, percpu=True)
            cpu_all.append(sum(cores) / len(cores))
            cpu_max_core.append(max(cores))
            temps.append(get_temp())
            powers.append(get_power_w())
            t_sample = time.time()
    return {
        "lat_mean": statistics.mean(latencies),
        "lat_sd": statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
        "cpu_all": statistics.mean(cpu_all),
        "cpu_max": statistics.mean(cpu_max_core),
        "temp": statistics.mean(temps),
        "power": statistics.mean(powers)
    }

# Carga CPU realista (inferência OpenCV DNN / convoluções densas 640x640)
dummy_img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
kernel = np.ones((5, 5), np.float32) / 25.0
def cpu_infer():
    res = cv2.resize(dummy_img, (640, 640))
    for _ in range(12):
        res = cv2.filter2D(res, -1, kernel)

print("A medir modo CPU Only (60s)...")
res_cpu = measure_system(60, cpu_infer)
print("CPU Only:", res_cpu)
