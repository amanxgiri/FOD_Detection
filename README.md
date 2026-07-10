# FOD Detection Prototype

Single-camera Foreign Object Debris detection prototype with a FastAPI backend,
React dashboard, live MJPEG stream, camera controls, and operator-started model
inference.

## What Is Included

- Backend API and runtime worker in `backend/`
- Frontend dashboard in `frontend/`
- Source model at `backend/models/weights/model_weight.pt`
- TensorRT engine at `backend/models/weights/model_weight.engine`
- TensorRT export and model validation scripts in `scripts/`

The committed TensorRT engine helps a compatible NVIDIA/CUDA/TensorRT machine
run the optimized path immediately. TensorRT engines are hardware/runtime
specific, so the default runtime is `auto`: try the `.engine` first, then fall
back to the portable `.pt` model when CUDA, TensorRT, or the engine is not
available.

## Runtime Modes

Set these in a root `.env` file only when you want to override the defaults.

```text
MODEL_RUNTIME=auto
MODEL_DEVICE=cuda:0
MODEL_FALLBACK_DEVICE=cpu
MODEL_CONFIDENCE_THRESHOLD=0.01
```

- `MODEL_RUNTIME=auto` tries TensorRT and automatically falls back to `.pt`.
- `MODEL_RUNTIME=tensorrt` requires the `.engine` and CUDA/TensorRT runtime.
- `MODEL_RUNTIME=pt` uses the `.pt` model on `MODEL_FALLBACK_DEVICE`.
- `MODEL_RUNTIME=cpu` forces the `.pt` model on CPU.

On Apple Silicon, you can try `MODEL_RUNTIME=pt` and
`MODEL_FALLBACK_DEVICE=mps`; keep `cpu` if your local PyTorch build does not
support MPS.

## Prerequisites

- Python 3.12 through 3.14
- Node.js and npm
- Optional for TensorRT: NVIDIA GPU, CUDA-compatible driver, and TensorRT
  Python packages from `backend/requirements.txt`

## Windows Setup

Run from the repository root. Use this path when you want the CUDA/TensorRT
packages installed.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

For a Windows machine without CUDA/TensorRT, install the portable dependency
set instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-cpu.txt
```

## macOS Setup

Run from the repository root.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-cpu.txt
```

The macOS path uses the `.pt` fallback. TensorRT is not required.

## Linux Setup

Run from the repository root.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements-cpu.txt
```

On a Linux NVIDIA/CUDA/TensorRT host, install `backend/requirements.txt`
instead of `backend/requirements-cpu.txt` to use the optimized engine path.

## Frontend Setup

```bash
cd frontend
npm install
cd ..
```

## Run The App

Start the backend from the repository root.

Windows:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

macOS/Linux:

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```bash
cd frontend
npm run dev
```

Open the dashboard at:

```text
http://127.0.0.1:5173
```

## Runtime Controls

The dashboard starts with the camera on and inference off.

- Use **Start Camera** / **Stop Camera** to control camera capture.
- Use **Start Inference** to load the configured model runtime.
- Use **Stop Inference** to stop the inference worker and unload the model.

With `MODEL_RUNTIME=auto`, Start Inference will use TensorRT when available and
fall back to the `.pt` model when CUDA/TensorRT is unavailable.

## TensorRT Engine Regeneration

Regenerate the engine on the target NVIDIA/CUDA/TensorRT machine whenever the
GPU, driver, CUDA, TensorRT, input size, or source `.pt` model changes.

```powershell
.\.venv\Scripts\python.exe scripts\export_tensorrt.py
.\.venv\Scripts\python.exe scripts\check_model.py --require-engine --load-engine
```

Use the same script names on macOS/Linux only for source-model checks; TensorRT
export itself requires an NVIDIA CUDA/TensorRT environment.

## Validation

Backend:

```bash
python -m pytest -q backend/tests
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```
