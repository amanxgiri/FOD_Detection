# Three-Camera FOD Detection Prototype

Real-time Foreign Object Debris detection using three independent camera feeds
and three distinct TensorRT engines. The feeds are not stitched. A single
round-robin scheduler runs only one engine at a time in this fixed order:

```text
camera_1 + model_1.engine
camera_2 + model_2.engine
camera_3 + model_3.engine
repeat
```

Capture continues independently on all cameras. Each camera is inferenced once
per three scheduler slots, avoiding concurrent TensorRT execution and its GPU
contention. The dashboard shows camera 1 and camera 2 on the upper row and camera
3 centered below them.

## Prerequisites

- Python 3.12 through 3.14
- Node.js `20.19+` or `22.12+` and npm (required by the locked Vite version)
- NVIDIA CUDA-capable GPU
- CUDA/TensorRT-compatible driver and Python packages
- Three Raspberry Pi cameras publishing independent RTSP streams
- Three distinct TensorRT engine files built for the deployment machine

## Installation

Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm install
cd ..
```

The CPU requirements can run unit tests and non-inference development, but the
three-model deployment runtime is strict TensorRT and does not fall back to
`.pt` inference.

## Linux Deployment (Ubuntu 22.04/24.04)

The application code is Linux-compatible and uses portable `pathlib`, threading,
OpenCV, FastAPI, and filesystem APIs. The required deployment path is Linux with
an NVIDIA GPU. TensorRT engines are serialized platform- and hardware-specific:
do not copy or reuse `.engine` files built on Windows. Build them on the target
Linux machine from the corresponding `.pt` files.

### 1. Install system prerequisites

On Ubuntu/Debian, install Python tooling, camera tools, and the shared libraries
commonly required by OpenCV:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip curl ca-certificates \
  ffmpeg netcat-openbsd \
  libgl1 libglib2.0-0 libsm6 libxext6 libxrender1
```

Install Node.js `20.19+` or `22.12+` using NodeSource, `nvm`, or your managed
Linux image. Do not rely on an older distribution-default Node package. Verify:

```bash
node --version
npm --version
```

Install a compatible NVIDIA driver and verify the GPU before installing Python
dependencies:

```bash
nvidia-smi
```

This repository currently pins the CUDA 12.6 PyTorch wheels and the CUDA 12
TensorRT Python package. The installed NVIDIA driver must support this stack.
If the deployment uses another CUDA major version, adjust the PyTorch index and
TensorRT package pins in `backend/requirements.txt` as one compatible set.

### 2. Create the virtual environment

Clone or copy the repository, change to its root, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r backend/requirements.txt
npm --prefix frontend install
```

Verify that PyTorch and TensorRT can access the GPU from this exact environment:

```bash
python -c "import torch; print(torch.__version__); print('CUDA:', torch.cuda.is_available()); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'unavailable')"
python -c "import tensorrt as trt; print('TensorRT:', trt.__version__)"
```

Do not continue until CUDA prints `True` and TensorRT imports successfully.
NVIDIA documents pip installation as a supported Python-development path on
current Ubuntu, Debian, RHEL, and SLES releases; see the
[TensorRT pip installation guide](https://docs.nvidia.com/deeplearning/tensorrt/latest/installing-tensorrt/install-pip.html).

### 3. Configure the Raspberry Pi RTSP/UDP streams

Each Raspberry Pi must run an RTSP server or publisher. A static IP by itself is
not a camera source: obtain the RTSP port, stream path, and credentials from the
service running on each Pi. Keep the Ubuntu host and all three Pis on the same
routed LAN or camera VLAN, preferably using router DHCP reservations and wired
Ethernet. Do not expose the RTSP ports directly to the public internet.

```bash
cp .env.example .env
```

Set the complete, independently readable RTSP URLs in `.env`:

```env
CAMERA_1_SOURCE=rtsp://viewer:password@192.168.1.21:8554/camera
CAMERA_2_SOURCE=rtsp://viewer:password@192.168.1.22:8554/camera
CAMERA_3_SOURCE=rtsp://viewer:password@192.168.1.23:8554/camera
```

Replace the sample addresses, `/camera` path, port, and credentials with the
actual Pi configuration. Percent-encode special characters in usernames and
passwords. Real credentials belong only in the ignored `.env`, never in
`.env.example` or Git.

RTSP performs session setup/control, normally on TCP port `554` or `8554`; with
UDP transport, the encoded video travels in negotiated RTP/RTCP UDP packets.
Allow the RTSP control port and the UDP range configured by the Pi RTSP servers
between the camera VLAN and Ubuntu. FFmpeg's default client range can span
ports 5000-65000, so a smaller fixed server range is easier to firewall.

Verify reachability and each complete stream URL before starting the backend:

```bash
ping -c 3 192.168.1.21
nc -vz 192.168.1.21 8554
ffprobe -rtsp_transport udp -v error \
  -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  'rtsp://viewer:password@192.168.1.21:8554/camera'
```

Repeat that check for `.22` and `.23`. Then validate OpenCV using the same UDP
transport that the application will use:

```bash
source .venv/bin/activate
export OPENCV_FFMPEG_CAPTURE_OPTIONS='rtsp_transport;udp'
export OPENCV_VIDEOIO_DEBUG=1
python scripts/check_camera.py --source 'rtsp://viewer:password@192.168.1.21:8554/camera' --timeout 10
python scripts/check_camera.py --source 'rtsp://viewer:password@192.168.1.22:8554/camera' --timeout 10
python scripts/check_camera.py --source 'rtsp://viewer:password@192.168.1.23:8554/camera' --timeout 10
```

`OPENCV_FFMPEG_CAPTURE_OPTIONS` is a process environment variable; exporting it
in the shell ensures OpenCV sees it. `OPENCV_VIDEOIO_DEBUG=1` makes the selected
capture backend visible in logs. Confirm that it reports FFmpeg. FFmpeg documents
the RTSP URL and UDP lower-transport behavior in its
[RTSP protocol documentation](https://ffmpeg.org/ffmpeg-protocols.html#rtsp).

Finally, open all three feeds at the same time (with `ffplay`, VLC, or three
`ffmpeg` processes) to verify aggregate network capacity and that each Pi allows
a client. At 4 Mbit/s per camera, plan for at least 12 Mbit/s plus protocol and
Wi-Fi overhead. Configure the cameras consistently—H.264, matching resolution
and frame rate, controlled bitrate, and a short keyframe interval are practical
defaults for low-latency verification.

### 4. Prepare models on Linux

Place the source models at:

```text
backend/models/weights/model_1.pt
backend/models/weights/model_2.pt
backend/models/weights/model_3.pt
```

Delete or move aside any engines copied from Windows or another GPU. On first
backend startup, each missing engine is built automatically from its matching
`.pt` file. To validate export explicitly before startup:

```bash
python scripts/export_tensorrt.py --check-prerequisites-only
python scripts/export_tensorrt.py --source backend/models/weights/model_1.pt --engine backend/models/weights/model_1.engine
python scripts/export_tensorrt.py --source backend/models/weights/model_2.pt --engine backend/models/weights/model_2.engine
python scripts/export_tensorrt.py --source backend/models/weights/model_3.pt --engine backend/models/weights/model_3.engine
```

### 5. Validate and run

Run automated checks from the repository root:

```bash
source .venv/bin/activate
python -m pytest -q backend/tests
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

Start the backend without reload for the normal Linux deployment. Avoid
`--reload` during TensorRT operation because the reloader creates an additional
process and may restart during engine generation or while cameras are open:

```bash
source .venv/bin/activate
export OPENCV_FFMPEG_CAPTURE_OPTIONS='rtsp_transport;udp'
export OPENCV_VIDEOIO_DEBUG=1
python -m uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```

Start the frontend development server in a second terminal:

```bash
npm --prefix frontend run dev -- --host 0.0.0.0
```

Open `http://<linux-host-ip>:5173`. Keep Uvicorn at one worker; multiple workers
would each try to own all cameras and GPU models. Ensure firewall rules permit
TCP ports `5173` and `8000` only from the intended network.

### 6. End-to-end RTSP acceptance test

With the backend and frontend running, first inspect system status:

```bash
curl -s http://127.0.0.1:8000/api/v1/system/status | python -m json.tool
```

Confirm all three entries in `camera_statuses` become `online`, then open
`http://<linux-host-ip>:5173` and verify camera 1 and 2 appear on the upper row,
camera 3 is centered below, and all three images update independently without
stitching.

Select **Start Inference**, wait several seconds, and query status twice:

```bash
curl -s http://127.0.0.1:8000/api/v1/system/status | python -m json.tool
sleep 2
curl -s http://127.0.0.1:8000/api/v1/system/status | python -m json.tool
```

Confirm all model statuses are `loaded`, inference is `running`, and the
scheduler slot count increases. The backend's single scheduler thread prevents
model `predict()` calls from overlapping; automated tests also verify the fixed
camera 1, camera 2, camera 3 order. Only detections mapped to the configured FOD
class should be drawn.

For recovery testing, stop one Pi stream temporarily. Its camera status should
leave `online` while the other feeds remain available and inference skips its
unavailable slots. Restart the stream and confirm that camera returns to
`online` without restarting the backend. All three cameras must be online for
the initial **Start Inference** operation.

For a persistent service, place a reverse proxy in front of the built frontend
and run the single-worker Uvicorn command under `systemd`. Add both OpenCV
variables above as `Environment=` entries in that service. The service user must
have read/write access to `backend/models/weights/` for automatic engine
creation and write access to `backend/data/` for SQLite and evidence images.

## Environment Configuration

Create the root `.env` from the supplied example:

```powershell
Copy-Item .env.example .env
```

Configure these required camera and engine values:

```env
CAMERA_1_SOURCE=rtsp://viewer:password@192.168.1.21:8554/camera
CAMERA_2_SOURCE=rtsp://viewer:password@192.168.1.22:8554/camera
CAMERA_3_SOURCE=rtsp://viewer:password@192.168.1.23:8554/camera

MODEL_1_ENGINE_PATH=backend/models/weights/model_1.engine
MODEL_2_ENGINE_PATH=backend/models/weights/model_2.engine
MODEL_3_ENGINE_PATH=backend/models/weights/model_3.engine
MODEL_1_SOURCE_PATH=backend/models/weights/model_1.pt
MODEL_2_SOURCE_PATH=backend/models/weights/model_2.pt
MODEL_3_SOURCE_PATH=backend/models/weights/model_3.pt

MODEL_RUNTIME=tensorrt
MODEL_DEVICE=cuda:0
MODEL_FOD_CLASS_ID=0
INFERENCE_IDLE_BACKOFF_SECONDS=0.001
```

A camera source may be an OpenCV camera index, video-file path, or supported
stream URL. Keep each engine permanently assigned to the corresponding camera.

The three capture threads continuously decode their independent streams and
keep only the latest frame. The inference scheduler still executes one model at
a time in the order camera 1, camera 2, camera 3. Each turn takes a non-blocking
snapshot of that camera's latest frame; it never waits for or drains queued
frames. This is scheduler ordering,
not exposure-level synchronization: exact cross-camera timing would require
clock synchronization (NTP/PTP), source timestamps, and additional application
logic.

## Creating the TensorRT Engines

Place the three distinct source models at:

```text
backend/models/weights/model_1.pt
backend/models/weights/model_2.pt
backend/models/weights/model_3.pt
```

When the backend starts, it checks each configured source/engine pair. If a
`model_N.pt` file exists but its corresponding `model_N.engine` does not, the
backend automatically exports that source to TensorRT before starting the camera
runtime. Existing engines are left untouched. Missing source-and-engine pairs
are not generated, but inference cannot start until all three required engines
exist. An automatic export failure stops backend startup with the camera/model
pair included in the error.

Automatic export can take several minutes on first startup and requires the
configured NVIDIA CUDA/TensorRT environment. Subsequent startups reuse the
existing engine files.

You can also export them manually on the target NVIDIA machine:

```powershell
.\.venv\Scripts\python.exe scripts\export_tensorrt.py --source backend\models\weights\model_1.pt --engine backend\models\weights\model_1.engine
.\.venv\Scripts\python.exe scripts\export_tensorrt.py --source backend\models\weights\model_2.pt --engine backend\models\weights\model_2.engine
.\.venv\Scripts\python.exe scripts\export_tensorrt.py --source backend\models\weights\model_3.pt --engine backend\models\weights\model_3.engine
```

TensorRT engines are GPU, CUDA, TensorRT, input-size, and model-version specific.
They are also not portable between Windows and Linux. Regenerate all affected
engines on the target deployment machine when the operating system, GPU, CUDA,
TensorRT, input size, or source model changes. NVIDIA documents this engine
portability limitation in the
[TensorRT support matrix](https://docs.nvidia.com/deeplearning/tensorrt/latest/getting-started/support-matrix.html).

## Run the Application

Start the backend from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. All three cameras start automatically. Select
**Start Inference** to load and warm the three engines sequentially, then start
the serialized round-robin scheduler. **Stop Camera** stops all three cameras;
**Stop Inference** stops the scheduler and unloads all engines.

## End-to-End Test

Run this procedure on the target NVIDIA deployment machine.

### 1. Validate configured files

```powershell
$requiredEngines = @(
  'backend\models\weights\model_1.engine',
  'backend\models\weights\model_2.engine',
  'backend\models\weights\model_3.engine'
)
$requiredEngines | ForEach-Object { "$_ exists: $(Test-Path -LiteralPath $_)" }
```

Every result must be `True`.

### 2. Validate each camera independently

Replace the sample indices if `.env` uses different paths:

```powershell
.\.venv\Scripts\python.exe scripts\check_camera.py --source 0 --timeout 5
.\.venv\Scripts\python.exe scripts\check_camera.py --source 1 --timeout 5
.\.venv\Scripts\python.exe scripts\check_camera.py --source 2 --timeout 5
```

Each command must report `camera check passed`.

### 3. Load and warm each engine independently

```powershell
.\.venv\Scripts\python.exe scripts\check_model.py --source backend\models\weights\model_1.pt --engine backend\models\weights\model_1.engine --require-engine --load-engine
.\.venv\Scripts\python.exe scripts\check_model.py --source backend\models\weights\model_2.pt --engine backend\models\weights\model_2.engine --require-engine --load-engine
.\.venv\Scripts\python.exe scripts\check_model.py --source backend\models\weights\model_3.pt --engine backend\models\weights\model_3.engine --require-engine --load-engine
```

### 4. Start backend and frontend

Use the commands in **Run the Application**, then check backend status:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/system/status | ConvertTo-Json -Depth 5
```

Before inference starts, all entries in `camera_statuses` should become
`online`. In the dashboard, confirm:

- camera 1 and camera 2 appear side by side;
- camera 3 appears centered on the row below;
- the images are independent and not stitched;
- each panel identifies its camera and assigned model.

### 5. Start and verify round-robin inference

Select **Start Inference**, wait several seconds, then run:

```powershell
$first = Invoke-RestMethod http://127.0.0.1:8000/api/v1/system/status
Start-Sleep -Seconds 2
$second = Invoke-RestMethod http://127.0.0.1:8000/api/v1/system/status
$first | ConvertTo-Json -Depth 5
$second | ConvertTo-Json -Depth 5
```

Verify:

- all `model_statuses` values are `loaded`;
- `inference_status` is `running`;
- `scheduler_slot_count` increases between samples;
- all three feeds continue updating;
- only the model's `FOD` class is displayed;
- backend logs show no engine-load or concurrent-execution errors.

The scheduler is implemented as one thread, so two model `predict()` calls cannot
overlap. Automated tests also assert the repeating order
`camera_1, camera_2, camera_3` and use a non-blocking lock to detect overlap.

### 6. Verify each stream endpoint

Open these URLs independently or request one test frame:

```powershell
Invoke-WebRequest 'http://127.0.0.1:8000/api/v1/cameras/camera_1/stream?frame_limit=1' -OutFile camera_1.mjpeg
Invoke-WebRequest 'http://127.0.0.1:8000/api/v1/cameras/camera_2/stream?frame_limit=1' -OutFile camera_2.mjpeg
Invoke-WebRequest 'http://127.0.0.1:8000/api/v1/cameras/camera_3/stream?frame_limit=1' -OutFile camera_3.mjpeg
```

## Automated Validation

Backend:

```powershell
.\.venv\Scripts\python.exe -m pytest -q backend\tests
```

Frontend:

```powershell
cd frontend
npm run typecheck
npm run build
```
