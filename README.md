# FOD Detection Prototype

Single-camera Foreign Object Debris detection prototype with a FastAPI backend,
React dashboard, live MJPEG stream, runtime camera controls, and TensorRT model
inference.

## What Is Included

- Backend API and runtime worker in `backend/`
- Frontend dashboard in `frontend/`
- Source model at `backend/models/weights/model_weight.pt`
- TensorRT engine at `backend/models/weights/model_weight.engine`
- TensorRT export and model validation scripts in `scripts/`

The committed TensorRT engine is included so a compatible NVIDIA/CUDA/TensorRT
machine can try inference immediately. TensorRT engines are still
hardware/runtime-specific. If engine loading fails on another machine,
regenerate it from `model_weight.pt`.

## Prerequisites

- Windows with PowerShell
- Python 3.12 through 3.14
- Node.js and npm
- NVIDIA GPU and driver compatible with the CUDA/TensorRT packages in
  `backend/requirements.txt`

## Backend Setup

Run from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

Validate that the source model and TensorRT engine are available:

```powershell
.\.venv\Scripts\python.exe scripts\check_model.py --require-engine --load-engine
```

If the engine does not load on your machine, regenerate it:

```powershell
.\.venv\Scripts\python.exe scripts\export_tensorrt.py
.\.venv\Scripts\python.exe scripts\check_model.py --require-engine --load-engine
```

## Frontend Setup

```powershell
cd frontend
npm install
cd ..
```

## Run The App

Start the backend from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

In a second terminal, start the frontend:

```powershell
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
- Use **Start Inference** to load the TensorRT engine and draw detections.
- Use **Stop Inference** to stop the inference worker and unload the model.

If no boxes are drawn, first check the system status panel. The current prototype
confidence threshold is intentionally low:

```text
MODEL_CONFIDENCE_THRESHOLD=0.01
```

You can override runtime settings by creating a `.env` file at the repository
root.

## Useful Checks

Camera:

```powershell
.\.venv\Scripts\python.exe scripts\check_camera.py --source 0 --timeout 5
```

Backend tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q backend\tests
```

Frontend checks:

```powershell
cd frontend
npm run typecheck
npm run build
```

## Common Issues

### TensorRT engine not found

Confirm that this file exists:

```text
backend/models/weights/model_weight.engine
```

Start the backend from the repository root so relative paths resolve correctly.

### TensorRT engine fails to load

The committed engine may not match your GPU, driver, CUDA, or TensorRT runtime.
Regenerate it with:

```powershell
.\.venv\Scripts\python.exe scripts\export_tensorrt.py
```

### Camera opens but no frames arrive

Close other camera apps, check Windows camera permissions, and run:

```powershell
.\.venv\Scripts\python.exe scripts\check_camera.py --source 0 --timeout 5
```
