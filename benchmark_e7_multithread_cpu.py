import time, subprocess, re, statistics, psutil, cv2
import numpy as np

cv2.setNumThreads(4)
print(f"OpenCV Threads ativas: {cv2.getNumThreads()}")

def get_temp():
    out = subprocess.check_output(["vcgencmd", "measure_temp"], text=True)
    return float(re.search(r"temp=([\d\.]+)", out).group(1))

def get_power_w():
    try:
        out = subprocess.check_output(["vcgencmd", "pmic_read_adc"], text=True)
        volts = dict(re.findall(r"(\S+)_V volt\(\d+\)=([\d\.]+)V", out))
        amps  = dict(re.findall(r"(\S+)_A current\(\d+\)=([\d\.]+)A", out))
        return sum(float(volts[k]) * float(amps[k]) for k in volts if k in amps)
    except Exception:
        return 0.0

dummy_img = np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)
kernel = np.ones((5, 5), np.float32) / 25.0

def cpu_infer_4threads():
    res = cv2.resize(dummy_img, (640, 640))
    for _ in range(12):
        res = cv2.filter2D(res, -1, kernel)

psutil.cpu_percent(interval=None, percpu=True)
cpu_all, cpu_max_core, temps, powers, latencies = [], [], [], [], []
t_start = time.time()
t_sample = t_start

while time.time() - t_start < 60.0:
    t0 = time.perf_counter()
    cpu_infer_4threads()
    latencies.append((time.perf_counter() - t0) * 1000.0)
    if time.time() - t_sample >= 1.0:
        cores = psutil.cpu_percent(interval=None, percpu=True)
        cpu_all.append(sum(cores) / len(cores))
        cpu_max_core.append(max(cores))
        temps.append(get_temp())
        powers.append(get_power_w())
        t_sample = time.time()

print("\n=== RESULTADO CPU 4-THREADS (TABELA II) ===")
print(f"Lat: {statistics.mean(latencies):.1f} ± {statistics.stdev(latencies):.2f} ms | CPU All: {statistics.mean(cpu_all):.1f}% | Max Core: {statistics.mean(cpu_max_core):.1f}% | Temp: {statistics.mean(temps):.1f} C | SoC Power: {statistics.mean(powers):.2f} W")
