import time, glob, psutil, cv2
import numpy as np
from picamera2 import Picamera2
from hailo_platform import (HEF, VDevice, HailoStreamInterface, InferVStreams,
                            ConfigureParams, InputVStreamParams, OutputVStreamParams, FormatType)

# Procura modelos compilados especificamente para HAILO8L (_h8l.hef)
hef_files = (glob.glob("/usr/share/hailo-models/*yolov8*h8l*.hef") or 
             glob.glob("/usr/share/hailo-models/**/*h8l*.hef", recursive=True) or
             glob.glob("/usr/share/hailo-models/*h8l*.hef"))

if not hef_files:
    print("AVISO: Nenhum ficheiro *h8l*.hef encontrado em /usr/share/hailo-models/. A procurar na pasta home...")
    hef_files = glob.glob("/home/kamacupa/**/*h8l*.hef", recursive=True)

if not hef_files:
    raise FileNotFoundError("Nenhum modelo HEF para HAILO8L encontrado. Execute 'find / -name \"*h8l*.hef\" 2>/dev/null' para localizar.")

hef_path = hef_files[0]
print(f"Modelo NPU HAILO8L carregado: {hef_path}")

hef = HEF(hef_path)
in_info = hef.get_input_vstream_infos()[0]
h, w, c = in_info.shape

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"}))
picam2.start()

psutil.cpu_percent(interval=None)
cpu_samples, infer_ms = [], []
frames = 0

with VDevice() as target:
    cfg = ConfigureParams.create_from_hef(hef=hef, interface=HailoStreamInterface.PCIe)
    ng = target.configure(hef, cfg)[0]
    ng_params = ng.create_params()
    in_params = InputVStreamParams.make(ng, format_type=FormatType.UINT8)
    out_params = OutputVStreamParams.make(ng, format_type=FormatType.FLOAT32)

    with InferVStreams(ng, in_params, out_params) as pipe:
        with ng.activate(ng_params):
            t_start = time.time()
            t_cpu = t_start
            while time.time() - t_start < 60.0:
                frame = picam2.capture_array()
                resized = cv2.resize(frame, (w, h))
                t0 = time.perf_counter()
                _ = pipe.infer({in_info.name: np.expand_dims(resized, axis=0)})
                infer_ms.append((time.perf_counter() - t0) * 1000.0)
                frames += 1
                if time.time() - t_cpu >= 1.0:
                    cpu_samples.append(psutil.cpu_percent(interval=None))
                    t_cpu = time.time()

elapsed = time.time() - t_start
picam2.stop()

print("\n================ RESULTADO HAILO-8L NPU (TABELA II) ================")
print(f"RPi 5 + Hailo NPU -> Avg. FPS: {frames/elapsed:.1f} | Inference: {sum(infer_ms)/len(infer_ms):.1f} ms | CPU Load: {sum(cpu_samples)/len(cpu_samples):.1f}%")
