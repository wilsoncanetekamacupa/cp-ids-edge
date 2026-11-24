import time, glob, subprocess, re, statistics, psutil, cv2
import numpy as np
from picamera2 import Picamera2
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams,
                            ConfigureParams, InputVStreamParams, OutputVStreamParams, FormatType)

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

hef_path = glob.glob("/usr/share/hailo-models/*yolov8*h8l*.hef")[0]
hef = HEF(hef_path)
in_info = hef.get_input_vstream_infos()[0]
h, w, _ = in_info.shape

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"}))
picam2.start()

psutil.cpu_percent(interval=None, percpu=True)
cpu_all, cpu_max_core, temps, powers, latencies = [], [], [], [], []

with VDevice() as target:
    cfg = ConfigureParams.create_from_hef(hef=hef, interface=HailoStreamInterface.PCIe)
    ng = target.configure(hef, cfg)[0]
    ng_params = ng.create_params()
    in_params = InputVStreamParams.make(ng, format_type=FormatType.UINT8)
    out_params = OutputVStreamParams.make(ng, format_type=FormatType.FLOAT32)

    with InferVStreams(ng, in_params, out_params) as pipe:
        with ng.activate(ng_params):
            t_start = time.time()
            t_sample = t_start
            while time.time() - t_start < 60.0:
                frame = picam2.capture_array()
                resized = cv2.resize(frame, (w, h))
                t0 = time.perf_counter()
                _ = pipe.infer({in_info.name: np.expand_dims(resized, axis=0)})
                latencies.append((time.perf_counter() - t0) * 1000.0)
                if time.time() - t_sample >= 1.0:
                    cores = psutil.cpu_percent(interval=None, percpu=True)
                    cpu_all.append(sum(cores) / len(cores))
                    cpu_max_core.append(max(cores))
                    temps.append(get_temp())
                    powers.append(get_power_w())
                    t_sample = time.time()

picam2.stop()
print("\n=== RESULTADO HAILO-8L NPU (TABELA II) ===")
print(f"Lat: {statistics.mean(latencies):.1f} ± {statistics.stdev(latencies):.2f} ms | CPU All: {statistics.mean(cpu_all):.1f}% | Max Core: {statistics.mean(cpu_max_core):.1f}% | Temp: {statistics.mean(temps):.1f} C | Power: {statistics.mean(powers):.2f} W")
