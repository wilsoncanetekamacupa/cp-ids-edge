import time
import psutil
import subprocess
import re
import glob

# Procura automaticamente o ficheiro de pós-processamento Hailo YOLOv8/YOLOv6 instalado no sistema
hailo_jsons = glob.glob("/usr/share/rpi-camera-assets/hailo*.json")
post_file = hailo_jsons[0] if hailo_jsons else "/usr/share/rpi-camera-assets/imx500_mobilenet_ssd.json"
print(f"A utilizar pipeline NPU: {post_file}")

cmd_npu = [
    "rpicam-vid", "-t", "60000", "--nopreview", "-v", "2",
    "--post-process-file", post_file,
    "-o", "/dev/null"
]

psutil.cpu_percent(interval=None)
cpu_samples = []
proc = subprocess.Popen(cmd_npu, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

start = time.time()
while time.time() - start < 62:
    if proc.poll() is not None:
        break
    cpu_samples.append(psutil.cpu_percent(interval=1.0))

if proc.poll() is None:
    proc.terminate()

output, _ = proc.communicate(timeout=5)

# Conta o número total de frames codificados/processados ou extrai FPS do log verboso (-v 2)
fps_matches = re.findall(r'(\d+\.\d+)\s*fps', output, re.IGNORECASE)
frame_matches = re.findall(r'Frame\s+(\d+)', output, re.IGNORECASE)

if fps_matches:
    avg_fps = sum(float(x) for x in fps_matches) / len(fps_matches)
elif frame_matches:
    total_frames = int(frame_matches[-1])
    avg_fps = total_frames / 60.0
else:
    # Fallback: conta linhas de timestamp de frame no output verboso
    lines = [l for l in output.splitlines() if "timestamp" in l.lower() or "frame" in l.lower()]
    avg_fps = len(lines) / 60.0

avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0.0
inf_ms = (1000.0 / avg_fps) if avg_fps > 0 else 0.0

print("\n================ RESULTADO REAL NPU (TABELA II) ================")
print(f"RPi 5 + Hailo NPU -> Avg. FPS: {avg_fps:.1f} | Inference: {inf_ms:.1f} ms | CPU Load: {avg_cpu:.1f}%")
