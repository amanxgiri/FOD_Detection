## Technical Design and Implementation Specification

**Document Status:** Initial Technical Specification  
**Project Type:** Single-Camera Real-Time FOD Detection Prototype  
**Primary Purpose:** Implementation specification for Codex  
**Primary Backend Language:** Python  
**Frontend:** React + TypeScript  
**Architecture Status:** Approved prototype baseline

---

# 1. Project Overview

The purpose of this project is to build a prototype application that performs real-time Foreign Object Debris (FOD) detection from a single camera feed.

A trained object-detection model already exists and its saved model weights will be integrated into the application for inference.

The model weights will be supplied to the project as:

```text
model_weight.pt
```

The supplied `.pt` file is the source model artifact. The prototype deployment workflow must convert this model to a TensorRT engine and use the generated engine for runtime inference on the NVIDIA GPU.

The prototype must:

1. capture frames continuously from one camera;
    
2. run trained-model inference on the captured frames;
    
3. post-process model detections;
    
4. optionally validate detections across multiple recent frames;
    
5. display an annotated live feed in a browser;
    
6. generate real-time FOD alerts;
    
7. save confirmed detection metadata;
    
8. save evidence images for confirmed detections;
    
9. allow an operator to view and acknowledge alerts;
    
10. expose basic performance and system-health information.
    

This project is a **prototype**, not a production airport deployment.

The implementation must therefore remain modular and maintainable without introducing unnecessary production-scale infrastructure.

---

# 2. Prototype Scope

## 2.1 Included in Scope

The initial prototype includes:

- one physical camera;
    
- one model loaded into memory;
    
- real-time frame capture;
    
- real-time inference;
    
- confidence filtering;
    
- bounding-box rendering;
    
- optional temporal detection validation;
    
- annotated browser video stream;
    
- real-time FOD alert events;
    
- detection history;
    
- alert acknowledgement;
    
- evidence-image storage;
    
- SQLite metadata storage;
    
- camera health reporting;
    
- inference performance reporting;
    
- smoke tests;
    
- validation tests;
    
- regression testing after changes.
    

---

## 2.2 Explicitly Out of Scope

The following must not be implemented in the first prototype unless the specification is intentionally revised later:

- multiple cameras;
    
- camera synchronization;
    
- camera calibration workflows;
    
- image stitching;
    
- panoramic frame generation;
    
- multi-view fusion;
    
- cross-camera tracking;
    
- distributed inference;
    
- Kubernetes;
    
- message brokers such as Kafka or RabbitMQ;
    
- cloud object storage;
    
- user authentication;
    
- role-based access control;
    
- automatic runway closure decisions;
    
- integration with airport operational systems;
    
- SMS or email alert delivery;
    
- multi-model ensemble inference;
    
- anomaly-detection models;
    
- automatic model retraining;
    
- remote model registry integration.
    

The repository architecture should allow future development, but Codex must not prematurely implement these capabilities.

---
# 3. Incremental Development and Testing Strategy

This project must **not be implemented as one large, complete system in a single development pass**.

Codex must build the project incrementally using small, independently testable modules and milestones.

The required development approach is:

```text
Select one small module or milestone
              │
              ▼
Implement only that scope
              │
              ▼
Run module-specific tests
              │
              ▼
Run smoke tests
              │
              ▼
Run validation tests
              │
              ▼
Run relevant regression tests
              │
              ▼
Fix any failures
              │
              ▼
Repeat tests until passing
              │
              ▼
Integrate with existing modules
              │
              ▼
Validate the integrated system
              │
              ▼
Proceed to the next module
```

The implementation must **not** follow this approach:

```text
Camera
+ Inference
+ FastAPI
+ Database
+ WebSocket
+ React Dashboard
+ Alerts
+ Temporal Validation
+ Monitoring
        │
        ▼
Implement everything together
        │
        ▼
Test only after completion
```

This approach is explicitly prohibited because failures become difficult to isolate and changes in one subsystem may silently break another subsystem.

Instead, development must proceed in small stages.

For example:

```text
Stage 1
Repository setup
    ↓
Test

Stage 2
Camera capture
    ↓
Test camera module
    ↓
Run smoke tests

Stage 3
Frame buffer
    ↓
Test buffer independently
    ↓
Test camera + buffer integration
    ↓
Run smoke and regression tests

Stage 4
Model loading
    ↓
Test model independently
    ↓
Run inference on known test image
    ↓
Run smoke and regression tests

Stage 5
Live inference pipeline
    ↓
Test capture + buffer + inference
    ↓
Validate frame skipping behavior
    ↓
Run regression tests

Stage 6
Video streaming
    ↓
Test stream independently
    ↓
Validate existing inference pipeline
    ↓
Run regression tests

Stage 7
Frontend
    ↓
Test frontend independently
    ↓
Integrate with backend
    ↓
Validate full camera-to-browser path

Stage 8
Persistence and alerts
    ↓
Test storage independently
    ↓
Test WebSocket independently
    ↓
Integrate
    ↓
Run complete regression suite
```

## 3.1 Small Module Requirement

Each module should be implemented with a clear responsibility and tested before depending modules are added.

Examples include:

```text
CameraManager
LatestFrameBuffer
ModelAdapter
InferenceEngine
PostProcessor
TemporalValidator
FrameRenderer
EvidenceStore
DetectionRepository
AlertManager
WebSocketConnectionManager
PerformanceMonitor
```

Codex must avoid implementing several unrelated modules in one large change when they can be developed and validated separately.

---

## 3.2 Test Before Integration

A module must first be tested independently where practical.

Example:

```text
CameraManager
      │
      ▼
Test:
- camera opens
- frame is returned
- timestamps exist
- sequence IDs increase
- failed reads are handled
- camera releases correctly
```

Only after this module works should it be integrated with:

```text
CameraManager
      │
      ▼
LatestFrameBuffer
```

The integrated pair must then be tested before adding the inference engine.

The expected progression is:

```text
CameraManager
      ↓
TEST

CameraManager
      +
LatestFrameBuffer
      ↓
TEST

CameraManager
      +
LatestFrameBuffer
      +
ModelAdapter
      ↓
TEST

CameraManager
      +
LatestFrameBuffer
      +
ModelAdapter
      +
InferenceEngine
      ↓
TEST
```

The same incremental approach applies to the backend API and frontend.

---

## 3.3 Mandatory Testing After Every Implementation Step

After implementing or modifying a module, Codex must perform the following sequence:

```text
1. Run tests specific to the modified module.

2. Run integration tests for components directly connected to that module.

3. Run the project smoke tests.

4. Run validation tests for the newly implemented behavior.

5. Run relevant regression tests for previously working functionality.

6. Fix all failures caused by the change.

7. Repeat the required tests.

8. Proceed only when the module and affected system paths are stable.
```

Testing must happen continuously throughout development.

Testing must **not** be treated as a final project phase.

---

## 3.4 Milestone Isolation Rule

At the beginning of each milestone, Codex must restrict implementation to the requirements of that milestone.

For example, while implementing the camera milestone:

```text
Allowed:
- CameraManager
- FramePacket
- camera configuration
- LatestFrameBuffer
- camera tests
- diagnostic script

Not yet required:
- WebSocket alerts
- SQLite persistence
- React alert cards
- temporal validation
```

Likewise, while implementing model integration, Codex must not simultaneously redesign the frontend.

The goal is to maintain small, understandable changes that can be tested and reviewed independently.

---

## 3.5 Definition of a Development Cycle

The standard development cycle for this repository is:

```text
DEFINE SMALL SCOPE
        ↓
IMPLEMENT
        ↓
UNIT TEST
        ↓
INTEGRATION TEST
        ↓
SMOKE TEST
        ↓
VALIDATION TEST
        ↓
REGRESSION TEST
        ↓
FIX
        ↓
RETEST
        ↓
DOCUMENT
        ↓
NEXT MODULE
```

This process is mandatory for all major modules and milestones in the project.

---

## 3.6 Explicit Instruction to Codex

Codex must follow the instruction below throughout the project:

> Do not attempt to generate and implement the complete FOD detection application in one pass. Build the system incrementally. Implement one small module or clearly bounded milestone at a time, test that implementation, validate its behavior, run smoke and relevant regression tests, fix any failures, and only then proceed to the next module. Previously working functionality must be revalidated after integration changes.

The goal of this development strategy is to make failures easier to isolate, reduce regressions, and ensure that every layer of the prototype is working before additional complexity is introduced.

---

# 4. Core Design Principles

## 4.1 Single Ownership of the Camera

Only the camera subsystem may directly interact with the camera device.

The API layer, frontend, inference engine, and alert manager must never open their own camera connections.

The camera must have one owner:

```text
Camera Device
      │
      ▼
CameraManager
      │
      ▼
LatestFrameBuffer
```

OpenCV's `VideoCapture` interface supports camera capture and frame reading, which makes it suitable for the prototype capture abstraction.

---

## 4.2 Capture and Inference Must Be Decoupled

The implementation must not use a single sequential loop containing all of the following:

```text
read camera
    ↓
run inference
    ↓
draw frame
    ↓
save detection
    ↓
send network response
    ↓
read next camera frame
```

Instead, camera capture and inference must run independently.

Required design:

```text
Camera Worker
      │
      ▼
Latest Frame Buffer
      │
      ▼
Inference Worker
      │
      ▼
Latest Inference Result
```

The primary goal is to prevent old frames from accumulating in an unbounded queue.

For this real-time monitoring prototype, recent information has greater value than processing every historical captured frame.

Therefore:

> The inference worker should process the newest available frame and may intentionally skip intermediate frames when inference is slower than camera capture.

This is an architectural requirement for this project.

---

## 4.3 Model Implementation Must Be Isolated

The complete application must not directly depend on model-specific inference calls.

All model interaction must occur behind a model adapter.

Required abstraction:

```text
Application
     │
     ▼
ModelAdapter
     │
     ├── load()
     ├── warmup()
     ├── predict()
     └── close()
     │
     ▼
Current Trained Model
```

The first adapter should support the format of the currently saved prototype model weights.

The initial expected weight path is:

```text
backend/models/weights/model_weight.pt
```

If the existing weights use an Ultralytics-compatible runtime, implement:

```text
UltralyticsModelAdapter
```

If the current saved weights require another runtime, the implementation must preserve the same adapter interface and replace only the adapter implementation.

The rest of the system must receive normalized application-level detection objects and must not depend on raw detector-library result objects.

### 4.3.1 Model Weight and TensorRT Deployment Path

The user will provide the trained model weights as:

```text
backend/models/weights/model_weight.pt
```

This `.pt` model is the source model artifact.

For the prototype runtime, the model must be exported to TensorRT engine format:

```text
model_weight.pt
        │
        ▼
TensorRT export
        │
        ▼
model_weight.engine
        │
        ▼
TensorRT runtime inference
        │
        ▼
NVIDIA GPU
```

The runtime inference pipeline must use:

```text
backend/models/weights/model_weight.engine
```

The `.pt` source model must be retained so that the TensorRT engine can be regenerated when the target GPU, CUDA, TensorRT, model input configuration, or deployment environment changes.

The export process must be implemented as a separate script:

```text
scripts/export_tensorrt.py
```

The export script must:

- load `model_weight.pt`;
- validate that an NVIDIA CUDA-capable GPU is available;
- export the model to TensorRT engine format;
- save the generated engine as `model_weight.engine`;
- report the export configuration;
- fail clearly when export cannot be completed;
- not silently fall back to CPU inference.

The TensorRT engine should be built on the intended deployment machine or in a deliberately compatible build environment.

Backend command examples in this document assume commands are run from the
repository root and that the backend virtual environment is located at:

```text
.venv
```

Do not mix virtual-environment paths. A shell error such as
`./.venv/Scripts/python.exe: No such file or directory` means the selected
virtual-environment path does not exist in the current checkout.

Dependency installation for a fresh deployment machine is:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

The backend requirements file includes the CUDA 12.x export and runtime stack:

```text
Python 3.12 through Python 3.14 compatible backend pins
PyTorch CUDA 12.6 wheels
Ultralytics
ONNX / ONNX Runtime GPU / ONNX Slim
NVIDIA TensorRT CUDA 12 Python runtime
NVIDIA ModelOpt plus explicitly pinned ONNX helper packages
```

Pydantic is pinned to a version whose `pydantic-core` wheel supports Python
3.14. Older Pydantic pins may try to build `pydantic-core` from source and fail
because their PyO3 build dependency does not support Python 3.14.

The default dependency set assumes an NVIDIA GPU and driver compatible with CUDA
12.x. If the deployment machine uses a different CUDA major version, the PyTorch
and TensorRT wheel lines in `backend/requirements.txt` must be adjusted before
installation. The prototype must still fail clearly rather than silently falling
back to CPU inference.

The expected deployment workflow is:

```powershell
.\.venv\Scripts\python.exe scripts\check_model.py
.\.venv\Scripts\python.exe scripts\export_tensorrt.py
.\.venv\Scripts\python.exe scripts\check_model.py --require-engine --load-engine
```

The backend development server is started from the repository root with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

The equivalent Git Bash path is:

```bash
./.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

The user-supplied `model_weight.pt` is committed or uploaded as the portable
source artifact. The generated `model_weight.engine` is hardware/runtime-specific
and must be regenerated on the target deployment machine when the GPU, driver,
CUDA, TensorRT, input size, or model version changes. Generated `.engine` and
intermediate `.onnx` files are ignored by git.

After export, the generated engine must be validated before integration into the live inference pipeline.

Validation must include:

```text
[ ] TensorRT engine file exists
[ ] TensorRT engine loads successfully
[ ] inference runs on the NVIDIA GPU
[ ] known test image can be processed
[ ] output detections can be normalized
[ ] output shape and class mapping are correct
[ ] no unexpected numerical or detection-format regression is introduced
[ ] inference latency is measured
```

The runtime model adapter should load `model_weight.engine` for normal prototype inference.

The source `model_weight.pt` should not be used as the default runtime model after the TensorRT engine has been successfully created and validated.

---

## 4.4 Critical Configuration Must Not Be Hard-Coded

The following must be configurable:

- camera source;
    
- model path;
    
- inference image size;
    
- model confidence threshold;
    
- IoU threshold;
    
- compute device;
    
- temporal validation enabled or disabled;
    
- temporal validation window size;
    
- required detection count;
    
- temporal matching IoU;
    
- evidence directory;
    
- database URL;
    
- frontend origin;
    
- JPEG quality;
    
- log level.
    

---

# 5. Approved Technology Stack

## 5.1 Backend

Use:

```text
Python
FastAPI
Uvicorn
Pydantic
pydantic-settings
OpenCV
NumPy
PyTorch or current model runtime
Ultralytics export/runtime tooling
ONNX export tooling
NVIDIA CUDA
NVIDIA TensorRT
NVIDIA ModelOpt
SQLAlchemy
SQLite
pytest
```

FastAPI supports standard API endpoints, WebSockets, streaming response classes, and application lifespan handling. These capabilities are used by this design for REST APIs, real-time events, video streaming, and controlled initialization and shutdown.

PyTorch provides inference mode for workloads where operations do not require autograd. Where the current model runtime uses standard PyTorch inference, model execution should use the appropriate inference-only execution mode.

SQLAlchemy will provide the backend persistence abstraction over the prototype SQLite database. SQLAlchemy describes itself as a Python SQL toolkit and object-relational mapper.

The target inference hardware for this prototype is an NVIDIA CUDA-capable GPU. The supplied `model_weight.pt` model must be exported to a TensorRT `model_weight.engine` artifact, and the validated TensorRT engine must be used for the normal runtime inference path.

CPU inference is not the intended deployment path for this prototype and must not be used as an automatic silent fallback.

---

## 5.2 Frontend

Use:

```text
React
TypeScript
Vite
Tailwind CSS
```

React provides the component model used to divide the operator interface into live-video, alert, history, status, and metric components.

Vite provides the frontend development and production build workflow for this separate browser application.

---

## 5.3 Communication

Use a hybrid communication model:

```text
HTTP video stream
        +
REST APIs
        +
WebSocket event channel
```

Responsibilities:

```text
HTTP stream:
    annotated live video

REST:
    historical and request-response data

WebSocket:
    real-time alerts and status events
```

FastAPI provides WebSocket handling and streaming-response facilities required by this communication design.

---

# 6. High-Level System Architecture

```text
                         PHYSICAL CAMERA
                                │
                                ▼
                    ┌─────────────────────┐
                    │    CameraManager    │
                    │                     │
                    │ OpenCV VideoCapture │
                    │ reconnect logic     │
                    │ camera status       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ LatestFrameBuffer   │
                    │                     │
                    │ bounded             │
                    │ thread-safe         │
                    │ latest-frame only   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  InferenceEngine    │
                    │                     │
                    │ ModelAdapter        │
                    │ inference timing    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    PostProcessor    │
                    │                     │
                    │ confidence filter   │
                    │ coordinate cleanup  │
                    │ normalization       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ TemporalValidator   │
                    │                     │
                    │ configurable        │
                    │ confirmation logic  │
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
      Annotated Frame     AlertManager      EvidenceStore
             │                 │                 │
             │                 ▼                 ▼
             │          DetectionRepository   JPEG files
             │                 │
             │                 ▼
             │               SQLite
             │
             ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │                     │
                    │ video stream        │
                    │ REST API            │
                    │ WebSocket events    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  React Dashboard    │
                    │                     │
                    │ live video          │
                    │ active alert        │
                    │ recent detections   │
                    │ system status       │
                    │ performance data    │
                    └─────────────────────┘
```

---

# 7. Primary Runtime Data Flow

## 7.1 Normal Frame Flow

```text
1. CameraManager captures frame
2. Frame receives sequence number and timestamp
3. LatestFrameBuffer replaces previous frame
4. InferenceEngine requests latest unprocessed frame
5. ModelAdapter performs prediction
6. Model output is normalized
7. PostProcessor applies filters
8. TemporalValidator updates recent detection state
9. Bounding boxes are rendered
10. Latest annotated frame becomes available to stream endpoint
11. Metrics are updated
```

---

## 7.2 Confirmed FOD Flow

```text
Model Detection
       │
       ▼
Post-processing
       │
       ▼
Temporal Validation
       │
       ▼
Confirmed Detection
       │
       ├──────────► save evidence image
       │
       ├──────────► create database record
       │
       └──────────► emit WebSocket event
                              │
                              ▼
                       React dashboard
                              │
                              ▼
                       operator alert
```

---

# 8. Repository Structure

Codex must create the following baseline structure.

```text
fod-detection-prototype/
│
├── backend/
│   │
│   ├── app/
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   │
│   │   │   ├── routes/
│   │   │   │   ├── health.py
│   │   │   │   ├── stream.py
│   │   │   │   ├── detections.py
│   │   │   │   ├── config.py
│   │   │   │   └── system.py
│   │   │   │
│   │   │   └── websocket/
│   │   │       ├── connection_manager.py
│   │   │       └── events.py
│   │   │
│   │   ├── camera/
│   │   │   ├── camera_manager.py
│   │   │   ├── frame_buffer.py
│   │   │   └── types.py
│   │   │
│   │   ├── inference/
│   │   │   ├── model_adapter.py
│   │   │   ├── model_loader.py
│   │   │   ├── inference_engine.py
│   │   │   ├── postprocessor.py
│   │   │   ├── renderer.py
│   │   │   └── types.py
│   │   │
│   │   ├── detection/
│   │   │   ├── temporal_validator.py
│   │   │   ├── detection_service.py
│   │   │   └── types.py
│   │   │
│   │   ├── alerts/
│   │   │   ├── alert_manager.py
│   │   │   └── types.py
│   │   │
│   │   ├── storage/
│   │   │   ├── database.py
│   │   │   ├── models.py
│   │   │   ├── evidence_store.py
│   │   │   │
│   │   │   └── repositories/
│   │   │       └── detection_repository.py
│   │   │
│   │   ├── monitoring/
│   │   │   ├── performance_monitor.py
│   │   │   └── system_monitor.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── detection.py
│   │   │   ├── alert.py
│   │   │   ├── config.py
│   │   │   └── system.py
│   │   │
│   │   └── core/
│   │       ├── config.py
│   │       ├── logging.py
│   │       └── lifecycle.py
│   │
│   ├── models/
│   │   └── weights/
│   │       └── best.pt
│   │
│   ├── data/
│   │   ├── detections/
│   │   └── fod.db
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── regression/
│   │   └── fixtures/
│   │
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/
│   │
│   ├── src/
│   │   ├── components/
│   │   │   ├── LiveCamera.tsx
│   │   │   ├── ActiveAlert.tsx
│   │   │   ├── DetectionCard.tsx
│   │   │   ├── DetectionList.tsx
│   │   │   ├── SystemStatus.tsx
│   │   │   └── PerformanceMetrics.tsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── DetectionHistory.tsx
│   │   │   └── Settings.tsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useDetectionSocket.ts
│   │   │   ├── useDetections.ts
│   │   │   └── useSystemStatus.ts
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── websocket.ts
│   │   │
│   │   ├── types/
│   │   │   ├── detection.ts
│   │   │   ├── alert.ts
│   │   │   └── system.ts
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── tests/
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── scripts/
│   ├── check_camera.py
│   ├── check_model.py
│   ├── export_tensorrt.py
│   └── smoke_test.py
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── INFERENCE_PIPELINE.md
│   ├── TESTING.md
│   └── DEVELOPMENT.md
│
├── .gitignore
├── docker-compose.yml
└── README.md
```

---

# 9. Backend Application Lifecycle

Application startup and shutdown must be controlled through FastAPI lifespan handling. FastAPI documents the `lifespan` mechanism for startup and shutdown logic.

## 9.1 Startup Order

The required startup order is:

```text
1. Load configuration
2. Configure logging
3. Initialize database
4. Validate TensorRT engine path
5. Verify NVIDIA GPU and TensorRT runtime availability
6. Load `model_weight.engine`
7. Warm up model where supported
8. Initialize camera
9. Validate camera connection
10. Start capture worker
11. Start inference worker
12. Initialize WebSocket manager
13. Mark system ready
```

The health endpoint must not report the system as fully ready before all critical components have initialized.

---

## 9.2 Shutdown Order

Required shutdown:

```text
1. Mark system as shutting down
2. Stop accepting new long-running operations
3. Stop inference worker
4. Stop camera worker
5. Release camera
6. Close model resources where required
7. close database resources
8. close WebSocket connections
9. complete process shutdown
```

Shutdown logic must be idempotent.

Calling stop or close more than once must not cause an application crash.

---

# 10. Camera Subsystem

## 10.1 CameraManager Responsibilities

File:

```text
backend/app/camera/camera_manager.py
```

Responsibilities:

- create camera connection;
    
- verify camera availability;
    
- continuously capture frames;
    
- timestamp frames;
    
- assign monotonically increasing sequence numbers;
    
- publish frames to `LatestFrameBuffer`;
    
- report camera status;
    
- detect failed reads;
    
- attempt controlled reconnection;
    
- release camera during shutdown.
    

OpenCV documents `VideoCapture` operations for opening cameras, reading frames, checking initialization status, and releasing the capture resource.

---

## 10.2 Required Interface

Conceptual interface:

```python
class CameraManager:
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def is_running(self) -> bool:
        ...

    def get_status(self) -> CameraStatus:
        ...

    def _capture_loop(self) -> None:
        ...
```

---

## 10.3 FramePacket Data Type

```python
@dataclass(frozen=True)
class FramePacket:
    sequence_id: int
    captured_at: datetime
    frame: np.ndarray
```

The raw frame object should not be exposed to the frontend or serialized through REST.

---

## 10.4 Camera Source Configuration

The source must be configurable.

Example:

```env
CAMERA_SOURCE=0
```

The implementation should also support a local video file as an alternate input source for development and repeatable testing.

OpenCV's `VideoCapture` interface accepts camera devices and video sources, which supports this testability requirement.

Example:

```env
CAMERA_SOURCE=backend/tests/fixtures/test_runway.mp4
```

---

## 10.5 Windows Camera Read Diagnostics

On Windows, OpenCV may successfully open a camera device and then fail while
reading the first frame. This is a camera-source failure, not a FastAPI startup
failure.

Example diagnostic log pattern:

```text
CvCapture_MSMF::grabFrame videoio(MSMF): can't grab frame
camera disconnected
camera reconnect attempt
```

When this occurs, the required diagnostic path is:

```powershell
.\.venv\Scripts\python.exe scripts\check_camera.py --source 0 --timeout 5
```

If the same source fails in the diagnostic script, investigate the camera source
before treating the browser dashboard or API as broken:

- close any other application using the camera;
- verify Windows camera privacy permissions;
- verify the configured `CAMERA_SOURCE`;
- try another camera index such as `1`;
- use a local video fixture to confirm the backend stream path still works.

The application must treat this as a camera read failure, mark camera status as
degraded or offline, and continue controlled reconnect attempts instead of
terminating the API process.

---

# 11. Latest Frame Buffer

File:

```text
backend/app/camera/frame_buffer.py
```

The latest-frame buffer is a critical component.

It must:

- be bounded;
    
- store only the newest required frame state;
    
- be thread-safe;
    
- allow the inference worker to wait for a newer sequence number;
    
- prevent unlimited memory growth.
    

Conceptual interface:

```python
class LatestFrameBuffer:
    def publish(self, packet: FramePacket) -> None:
        ...

    def get_latest(self) -> FramePacket | None:
        ...

    def wait_for_newer(
        self,
        last_sequence_id: int,
        timeout: float | None = None,
    ) -> FramePacket | None:
        ...
```

The implementation must not maintain an unbounded `queue.Queue` of camera frames.

---

# 12. Model Adapter

File:

```text
backend/app/inference/model_adapter.py
```

Define a model-independent interface.

Conceptual interface:

```python
from typing import Protocol

class ModelAdapter(Protocol):
    def load(self) -> None:
        ...

    def warmup(self) -> None:
        ...

    def predict(self, frame: np.ndarray) -> list[RawDetection]:
        ...

    def close(self) -> None:
        ...
```

The application must not pass raw model-framework objects outside the inference package.

---

## 12.1 Normalized RawDetection

```python
@dataclass(frozen=True)
class RawDetection:
    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
```

All coordinates at this level refer to the original frame coordinate system.

---

# 13. Inference Engine

File:

```text
backend/app/inference/inference_engine.py
```

## Responsibilities

The inference engine must:

1. wait for a new frame;
    
2. skip already processed sequence IDs;
    
3. call the model adapter;
    
4. measure inference latency;
    
5. send results to post-processing;
    
6. send normalized results to temporal validation;
    
7. update the annotated-frame store;
    
8. update performance metrics.
    

Conceptual interface:

```python
class InferenceEngine:
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def is_running(self) -> bool:
        ...

    def _inference_loop(self) -> None:
        ...
```

Where the current runtime is based on PyTorch, inference-only execution should use the appropriate PyTorch inference context when compatible with the model implementation. PyTorch documents `inference_mode` as an inference-oriented mode that disables autograd-related work such as view tracking and version-counter updates.

---

# 14. Post-Processing

File:

```text
backend/app/inference/postprocessor.py
```

Responsibilities:

- reject detections below configured confidence;
    
- validate coordinate ordering;
    
- clip coordinates to frame bounds;
    
- reject invalid zero-area boxes;
    
- convert output into application detection objects;
    
- optionally perform additional model-specific suppression only when required.
    

The postprocessor must be deterministic for identical inputs and configuration.

Conceptual interface:

```python
class PostProcessor:
    def process(
        self,
        detections: list[RawDetection],
        frame_width: int,
        frame_height: int,
    ) -> list[Detection]:
        ...
```

---

# 15. Detection Data Model

Use an application-level type.

```python
@dataclass(frozen=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
```

Bounding box:

```python
@dataclass(frozen=True)
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int
```

Model-specific result types must not appear in:

- API routes;
    
- database repositories;
    
- WebSocket payload builders;
    
- frontend schemas.
    

---

# 16. Temporal Validation

File:

```text
backend/app/detection/temporal_validator.py
```

## 16.1 Purpose

A single isolated prediction should not automatically have to become a confirmed FOD alert.

The temporal validator will allow detections to be confirmed from repeated observations across a configurable recent-frame window.

The initial implementation must remain simple.

Do not implement a complex tracking algorithm in the prototype unless later evidence demonstrates that one is needed.

---

## 16.2 Conceptual Flow

```text
Current Detection
        │
        ▼
Find spatially compatible recent detection
        │
        ▼
Update candidate history
        │
        ▼
Candidate appears sufficiently often?
        │
       Yes
        │
        ▼
Confirmed Detection
```

---

## 16.3 Configuration

Example configurable values:

```env
TEMPORAL_VALIDATION_ENABLED=true
TEMPORAL_WINDOW_SIZE=5
TEMPORAL_REQUIRED_HITS=3
TEMPORAL_MATCH_IOU=0.30
```

These values are **prototype starting parameters, not validated final values**.

They must be tuned using real camera footage and recorded false-positive and false-negative behavior.

Codex must not present these values as scientifically optimized.

---

## 16.4 Matching Rule

For the initial prototype, candidate matching may use:

```text
same class
    AND
bounding-box IoU >= configured matching threshold
```

The implementation must be unit tested with:

- persistent detections;
    
- intermittent detections;
    
- isolated false positive;
    
- spatially separate objects of the same class;
    
- object disappearing from the temporal window.
    

---

# 17. Detection Rendering

File:

```text
backend/app/inference/renderer.py
```

Responsibilities:

- copy the input frame before annotation;
    
- draw bounding boxes;
    
- display class label;
    
- display confidence value;
    
- optionally indicate provisional versus confirmed detection status;
    
- produce a frame ready for JPEG encoding.
    

Do not mutate the original raw camera frame in the camera buffer.

---

# 18. Alert Management

File:

```text
backend/app/alerts/alert_manager.py
```

Responsibilities:

- receive confirmed detections;
    
- create a stable alert event;
    
- prevent duplicate alert creation for the same confirmed candidate;
    
- save detection metadata;
    
- save evidence image;
    
- publish event to WebSocket subscribers;
    
- update alert state when acknowledged.
    

Conceptual flow:

```text
Confirmed Detection
        │
        ▼
Check duplicate state
        │
        ├── duplicate ──► update existing state
        │
        └── new
              │
              ▼
         Save evidence
              │
              ▼
         Save metadata
              │
              ▼
         Publish event
```

---

# 19. Evidence Storage

File:

```text
backend/app/storage/evidence_store.py
```

Evidence images must be stored locally for the prototype.

Directory:

```text
backend/data/detections/
```

Suggested structure:

```text
backend/data/detections/
├── 2026/
│   └── 07/
│       └── 07/
│           ├── DET-20260707-000001.jpg
│           ├── DET-20260707-000002.jpg
│           └── ...
```

The database should store a relative path rather than embedding image bytes in the SQLite database.

`EvidenceStore` interface:

```python
class EvidenceStore:
    def save(
        self,
        detection_id: str,
        frame: np.ndarray,
        timestamp: datetime,
    ) -> str:
        ...
```

The function returns the stored relative path.

---

# 20. Database Design

Use SQLite for prototype detection metadata.

Use SQLAlchemy as the persistence layer. SQLAlchemy provides Python database toolkit and ORM capabilities, and includes documented SQLite dialect support.

---

## 20.1 Detection Table

Minimum fields:

```text
detections
────────────────────────────────
id
event_timestamp
class_id
class_name
confidence
bbox_x1
bbox_y1
bbox_x2
bbox_y2
evidence_path
status
acknowledged_at
created_at
updated_at
```

Recommended status values:

```text
ACTIVE
ACKNOWLEDGED
```

---

## 20.2 Detection Repository

File:

```text
backend/app/storage/repositories/detection_repository.py
```

Required operations:

```python
create_detection(...)

get_detection(detection_id)

list_detections(
    limit,
    offset,
    status=None,
)

acknowledge_detection(
    detection_id,
    acknowledged_at,
)
```

Database logic must not be implemented directly inside API route files.

---

# 21. FastAPI REST API

All API endpoints should use:

```text
/api/v1
```

FastAPI response models should be used for structured REST responses. FastAPI documents that declared response models are used for response validation, serialization, filtering, and API documentation.

---

## 21.1 Health Endpoint

```http
GET /api/v1/health
```

Response:

```json
{
  "status": "ok",
  "ready": true,
  "camera": "online",
  "model": "loaded",
  "inference_worker": "running"
}
```

---

## 21.2 System Status

```http
GET /api/v1/system/status
```

Example response:

```json
{
  "camera_status": "online",
  "model_status": "loaded",
  "inference_status": "running",
  "capture_fps": 30.0,
  "inference_fps": 24.3,
  "average_inference_ms": 36.8,
  "latest_frame_age_ms": 41,
  "total_confirmed_detections": 12
}
```

Metrics must reflect measured application values.

Do not fabricate GPU metrics when the metric cannot be obtained from the active runtime.

---

## 21.3 Detection History

```http
GET /api/v1/detections
```

Query parameters:

```text
limit
offset
status
```

Example:

```json
{
  "items": [
    {
      "id": "DET-20260707-000001",
      "timestamp": "2026-07-07T09:02:18Z",
      "class_name": "Bolt",
      "confidence": 0.91,
      "status": "ACTIVE",
      "evidence_url": "/api/v1/detections/DET-20260707-000001/evidence"
    }
  ],
  "limit": 20,
  "offset": 0
}
```

---

## 21.4 Detection Detail

```http
GET /api/v1/detections/{detection_id}
```

Return one detection or HTTP 404 when no record exists.

---

## 21.5 Detection Evidence

```http
GET /api/v1/detections/{detection_id}/evidence
```

The backend must resolve the evidence path from the database.

The frontend must not be given unrestricted local filesystem paths.

---

## 21.6 Acknowledge Detection

```http
POST /api/v1/detections/{detection_id}/acknowledge
```

Expected behavior:

```text
ACTIVE
   ↓
ACKNOWLEDGED
```

Acknowledging an already acknowledged alert must be handled deterministically and must not crash the application.

---

## 21.7 Configuration Endpoint

Initial prototype:

```http
GET /api/v1/config
```

Optional runtime-adjustable fields may later use:

```http
PATCH /api/v1/config
```

Model path, database path, and camera device ownership settings should not be casually changed while the pipeline is running.

---

# 22. Video Streaming

Endpoint:

```http
GET /api/v1/stream
```

For the initial prototype, implement the live annotated feed as an HTTP streaming response using a multipart frame stream.

FastAPI provides `StreamingResponse` for streamed response bodies.

Conceptual pipeline:

```text
Latest annotated frame
        │
        ▼
JPEG encode
        │
        ▼
multipart stream frame
        │
        ▼
HTTP StreamingResponse
        │
        ▼
Browser
```

The video endpoint must consume the latest annotated frame.

It must not independently run model inference.

Incorrect:

```text
request arrives
    ↓
run model
    ↓
send frame
```

Correct:

```text
Inference worker continuously updates latest result

Stream endpoint:
    ↓
read latest annotated result
    ↓
encode/send
```

---

# 23. WebSocket Event Channel

Endpoint:

```text
/ws/events
```

FastAPI provides WebSocket endpoint support for persistent browser-server event communication.

The WebSocket is responsible for event notifications, not video transport.

---

## 23.1 Event Envelope

All events should follow a common envelope:

```json
{
  "type": "fod.detected",
  "timestamp": "2026-07-07T09:02:18Z",
  "data": {}
}
```

---

## 23.2 Required Event Types

Initial events:

```text
fod.detected
fod.acknowledged
camera.offline
camera.online
system.warning
```

---

## 23.3 FOD Detection Event Example

```json
{
  "type": "fod.detected",
  "timestamp": "2026-07-07T09:02:18Z",
  "data": {
    "detection_id": "DET-20260707-000001",
    "class_name": "Bolt",
    "confidence": 0.91,
    "bbox": {
      "x1": 540,
      "y1": 380,
      "x2": 608,
      "y2": 447
    },
    "evidence_url": "/api/v1/detections/DET-20260707-000001/evidence"
  }
}
```

---

# 24. Frontend Architecture

The browser interface should use React components with TypeScript types corresponding to API and WebSocket contracts.

React's documented component approach supports dividing the interface into independently maintained UI elements.

The first version must prioritize one main operator dashboard.

---

# 25. Dashboard Requirements

Suggested layout:

```text
┌───────────────────────────────────────────────────────────────────┐
│ FOD DETECTION SYSTEM       CAMERA ONLINE       MODEL READY        │
├────────────────────────────────────────────┬──────────────────────┤
│                                            │ ACTIVE ALERT         │
│                                            │                      │
│                                            │ Type: Bolt           │
│             LIVE CAMERA                   │ Confidence: 91%      │
│                                            │ Time: 14:32:18       │
│                     ┌─────┐                │                      │
│                     │ FOD │                │ [ACKNOWLEDGE]        │
│                     └─────┘                │ [VIEW EVIDENCE]      │
│                                            │                      │
├────────────────────────────────────────────┴──────────────────────┤
│ Capture FPS 30 | Inference FPS 24 | Latency 36 ms | Count 12     │
├───────────────────────────────────────────────────────────────────┤
│ RECENT DETECTIONS                                                 │
│                                                                   │
│ Bolt          91%       14:32:18       ACTIVE                     │
│ PlasticPart   87%       13:51:04       ACKNOWLEDGED               │
│ Wire          82%       12:42:11       ACKNOWLEDGED               │
└───────────────────────────────────────────────────────────────────┘
```

---

## 25.1 LiveCamera Component

File:

```text
frontend/src/components/LiveCamera.tsx
```

Responsibilities:

- display live backend stream;
    
- show offline placeholder when unavailable;
    
- display connection state;
    
- retry stream rendering when connectivity returns.
    

---

## 25.2 ActiveAlert Component

Responsibilities:

- show newest active confirmed alert;
    
- show evidence preview;
    
- show class name;
    
- show confidence;
    
- show event time;
    
- provide acknowledge action;
    
- prevent repeated acknowledge submission while request is in progress.
    

---

## 25.3 DetectionList

Responsibilities:

- show recent detection records;
    
- differentiate active and acknowledged states;
    
- open detection details;
    
- refresh after acknowledgement events.
    

---

## 25.4 SystemStatus

Display:

```text
Camera
Model
Inference worker
Backend connection
WebSocket connection
```

---

## 25.5 PerformanceMetrics

Display available measured metrics:

```text
Capture FPS
Inference FPS
Average inference latency
Latest frame age
Confirmed detection count
```

Unknown metrics must display an unavailable state rather than fabricated values.

---

# 26. Frontend and Backend Origins

During development, the frontend and backend may operate on separate origins.

FastAPI provides CORS middleware for browser frontend/backend communication across different origins.

The permitted frontend origin must be explicitly configured.

Example:

```env
FRONTEND_ORIGIN=http://localhost:5173
```

Do not default the deployed configuration to unrestricted origins.

---

# 27. Configuration Design

File:

```text
backend/app/core/config.py
```

Use a typed settings object.

Example environment variables:

```env
APP_ENV=development
LOG_LEVEL=INFO

CAMERA_SOURCE=0
CAMERA_RECONNECT_DELAY_SECONDS=2

MODEL_SOURCE_PATH=backend/models/weights/model_weight.pt
MODEL_ENGINE_PATH=backend/models/weights/model_weight.engine
MODEL_RUNTIME=tensorrt
MODEL_DEVICE=cuda:0
MODEL_CONFIDENCE_THRESHOLD=0.01
MODEL_IOU_THRESHOLD=0.50
MODEL_IMAGE_SIZE=640

TEMPORAL_VALIDATION_ENABLED=true
TEMPORAL_WINDOW_SIZE=5
TEMPORAL_REQUIRED_HITS=3
TEMPORAL_MATCH_IOU=0.30

DATABASE_URL=sqlite:///./data/fod.db
EVIDENCE_DIRECTORY=./data/detections

STREAM_JPEG_QUALITY=80

FRONTEND_ORIGIN=http://localhost:5173
```

Values shown here are configuration examples and initial prototype defaults. They must be validated against the actual camera, model, hardware, and real-world FOD footage.

---

# 28. Concurrency Model

The initial backend should use:

```text
Main FastAPI application
        │
        ├── API event loop
        │
        ├── Camera capture worker
        │
        └── Inference worker
```

The prototype must run with **one application worker process** because the current architecture assumes exclusive in-process ownership of:

- one physical camera;
    
- one loaded model;
    
- one shared latest-frame buffer;
    
- one inference pipeline.
    

Do not start several backend worker processes that each attempt to initialize the complete camera and model pipeline.

Horizontal scaling is outside prototype scope.

---

# 29. Thread Safety Requirements

Shared mutable runtime state must be protected.

The following require safe synchronization:

- latest raw frame;
    
- latest annotated frame;
    
- performance counters;
    
- worker running state;
    
- temporal candidate state;
    
- WebSocket event handoff.
    

Do not hold a shared lock while performing slow model inference.

Preferred sequence:

```text
Acquire frame lock
        ↓
obtain frame reference/copy
        ↓
release lock
        ↓
run inference
```

Do not keep the camera buffer locked for the duration of model execution.

---

# 30. Monitoring and Metrics

File:

```text
backend/app/monitoring/performance_monitor.py
```

Minimum runtime metrics:

```text
capture_fps
inference_fps
last_inference_ms
average_inference_ms
frames_captured
frames_inferred
frames_skipped
confirmed_detection_count
latest_frame_timestamp
camera_read_failures
```

Use a rolling or bounded measurement approach.

Do not retain unlimited latency samples in memory.

---

# 31. Logging

Use structured, readable application logging.

Minimum important events:

```text
application startup
configuration loaded
model loading started
model loading completed
camera opening
camera opened
camera disconnected
camera reconnect attempt
camera reconnected
inference worker started
confirmed detection created
evidence image saved
database error
WebSocket error
application shutdown
```

Do not log every frame at normal logging levels.

Per-frame logs may only be enabled at a verbose diagnostic level.

---

# 32. Error Handling

## 32.1 Camera Failure

Required behavior:

```text
Camera read fails
        │
        ▼
mark camera degraded/offline
        │
        ▼
log failure
        │
        ▼
publish camera.offline event
        │
        ▼
controlled reconnect attempts
        │
        ▼
connection restored?
        │
       Yes
        │
        ▼
publish camera.online
```

Temporary camera failure must not terminate the entire API application.

Windows OpenCV/MSMF read failures, including `OnReadSample` or `can't grab
frame` logs after the camera reports opened, must follow this same path. They
should be surfaced as camera degraded/offline status and diagnosed with
`scripts/check_camera.py` against the exact configured source.

---

## 32.2 Model Load Failure

If the model cannot load:

- application readiness must be false;
    
- error must be logged clearly;
    
- inference worker must not start;
    
- health information must identify model failure.
    

The application must not silently continue while pretending that inference is operational.

---

## 32.3 Evidence Save Failure

A failed evidence-image write must:

- be logged;
    
- not crash the entire inference worker;
    
- leave a traceable detection record or controlled failure state;
    
- not emit an evidence URL for a nonexistent file.
    

---

## 32.4 Database Failure

Database exceptions must not be silently ignored.

Failures should be logged with enough context to diagnose the affected operation.

---

# 33. Testing Strategy

Testing is mandatory.

Testing is not deferred until the project is complete.

Every implementation milestone must end with:

```text
Implementation
      │
      ▼
Feature-specific tests
      │
      ▼
Smoke tests
      │
      ▼
Validation tests
      │
      ▼
Regression tests
      │
      ▼
Fix failures
      │
      ▼
Repeat tests
      │
      ▼
Milestone complete
```

A milestone with failing required tests is not complete.

---

# 34. Smoke Testing Requirements

Smoke tests answer:

> Does the critical application path still work at a basic level?

Required smoke checks:

```text
[ ] Python application imports successfully
[ ] configuration loads
[ ] database initializes
[ ] `model_weight.pt` source model is accessible
[ ] TensorRT export script can validate export prerequisites
[ ] `model_weight.engine` is accessible
[ ] TensorRT engine loads
[ ] inference executes on the configured NVIDIA GPU
[ ] camera source opens
[ ] frame can be captured
[ ] inference can run on one frame
[ ] inference result can be normalized
[ ] annotated frame can be produced
[ ] health endpoint responds
[ ] system status endpoint responds
[ ] video stream endpoint responds
[ ] WebSocket endpoint accepts connection
[ ] frontend installs
[ ] frontend type checking passes
[ ] frontend build succeeds
```

Camera-dependent smoke testing should support two modes:

```text
Mode A:
physical camera

Mode B:
known local test video
```

This allows repeatable development tests even when a physical camera is not connected.

---

# 35. Validation Testing Requirements

Validation tests answer:

> Does the newly implemented feature behave as specified?

Example: after implementing temporal validation, test:

```text
[ ] isolated detection is handled according to configured rules
[ ] repeated object becomes confirmed
[ ] separate objects are not merged incorrectly
[ ] expired candidates are removed
[ ] disabled temporal validation follows configured bypass behavior
```

Example: after implementing alert acknowledgement:

```text
[ ] active alert can be acknowledged
[ ] database status changes
[ ] acknowledged_at is populated
[ ] missing detection returns correct error
[ ] repeated acknowledgement is deterministic
[ ] history endpoint reflects new state
[ ] frontend updates state
```

---

# 36. Regression Testing Requirement

After every feature implementation or code modification, Codex must ensure the change has not broken previously working functionality.

Required workflow:

```text
1. Run tests for modified component.
2. Run integration tests for affected subsystem.
3. Run backend test suite.
4. Run frontend tests.
5. Run frontend type checking.
6. Run frontend production build.
7. Run smoke test.
8. Validate camera-to-dashboard critical path when the change affects runtime flow.
9. Fix failures.
10. Repeat until required tests pass.
```

Codex must not fix a new feature by disabling unrelated existing tests.

Existing tests may only be changed when:

- the underlying specification intentionally changed;
    
- the previous test was incorrect;
    
- the reason is documented.
    

---

# 37. Critical End-to-End Validation Path

The primary regression path is:

```text
Camera
   ↓
CameraManager
   ↓
LatestFrameBuffer
   ↓
InferenceEngine
   ↓
ModelAdapter
   ↓
PostProcessor
   ↓
TemporalValidator
   ↓
AlertManager
   ↓
EvidenceStore + Database
   ↓
FastAPI
   ├── Video Stream
   ├── REST API
   └── WebSocket
   ↓
React Dashboard
   ↓
Operator acknowledgement
   ↓
Database state update
```

Major architectural changes must validate the relevant parts of this path.

---

# 38. Definition of Done for Every Milestone

A milestone is complete only when:

```text
[ ] implementation is complete
[ ] code starts without unexpected startup errors
[ ] feature-specific tests pass
[ ] smoke tests pass
[ ] validation tests pass
[ ] regression tests pass
[ ] frontend type checking passes when frontend is affected
[ ] frontend production build passes when frontend is affected
[ ] critical existing functionality remains operational
[ ] no unexplained critical errors appear in logs
[ ] documentation is updated for changed interfaces or behavior
```

---

# 39. Implementation Milestones

Codex must implement incrementally.

Do not attempt to implement the full architecture in one unvalidated change.

---

## Milestone 1: Repository Foundation

Implement:

```text
backend structure
frontend Vite application
configuration loading
logging setup
health endpoint
basic tests
```

Validation:

```text
backend starts
health endpoint responds
frontend development app loads
frontend build succeeds
```

---

## Milestone 2: Camera Capture

Implement:

```text
CameraManager
FramePacket
LatestFrameBuffer
camera status
test video source
camera diagnostic script
```

Validation:

```text
camera opens
frames arrive
sequence IDs increase
timestamps exist
buffer exposes latest frame
camera releases cleanly
test video source works
```

Then run all smoke and regression tests.

---

## Milestone 3: Model Integration

Implement:

```text
ModelAdapter
model loader
TensorRT export script
`model_weight.pt` source-model handling
`model_weight.engine` generation
TensorRT runtime adapter
NVIDIA GPU inference configuration
one-frame TensorRT inference
normalized detections
model diagnostic script
```

Validation:

```text
`model_weight.pt` is accessible
TensorRT export completes successfully
`model_weight.engine` is created
TensorRT engine loads successfully
inference runs on the configured NVIDIA GPU
engine processes known frame
detections normalize correctly
empty detections are handled
device configuration behaves correctly
model failure is visible
TensorRT engine results are validated before live integration
```

Then run all smoke and regression tests.

---

## Milestone 4: Decoupled Live Inference

Implement:

```text
camera worker
latest-frame buffer
inference worker
post-processing
performance timing
```

Validation:

```text
capture continues independently
inference processes new frames
stale frame queue does not grow
workers stop cleanly
exceptions do not silently kill worker
metrics update
```

Then run all smoke and regression tests.

---

## Milestone 5: Annotated Video Streaming

Implement:

```text
renderer
latest annotated frame store
JPEG encoding
HTTP video stream
```

Validation:

```text
browser receives stream
boxes appear
labels appear
confidence appears
stream endpoint does not run inference itself
disconnecting viewer does not stop inference
```

Then run all smoke and regression tests.

---

## Milestone 6: React Dashboard

Implement:

```text
main dashboard
live camera component
system status component
performance metrics
backend API service
```

Validation:

```text
dashboard loads
stream is visible
status values display
backend connection failure is represented
frontend type check passes
frontend build passes
```

Then run all smoke and regression tests.

---

## Milestone 7: Detection Persistence and Evidence

Implement:

```text
SQLite database
SQLAlchemy models
DetectionRepository
EvidenceStore
detection REST API
evidence endpoint
```

Validation:

```text
detection persists
history returns record
detail endpoint returns record
evidence file exists
evidence endpoint returns correct image
database failure is handled
```

Then run all smoke and regression tests.

---

## Milestone 8: Temporal Validation

Implement:

```text
candidate state
matching logic
sliding window
confirmation logic
candidate expiry
```

Validation:

```text
persistent detections confirm
isolated detections behave according to configuration
separate objects remain separate
old state expires
configuration controls behavior
```

Then run all smoke and regression tests.

---

## Milestone 9: WebSocket Alerts

Implement:

```text
connection manager
event schema
fod.detected
camera.offline
camera.online
system.warning
frontend WebSocket hook
ActiveAlert UI
```

Validation:

```text
connection succeeds
event schema is correct
frontend receives event
alert appears
reconnection works
video stream still works
REST endpoints still work
```

Then run all smoke and regression tests.

---

## Milestone 10: Alert Acknowledgement

Implement:

```text
acknowledge API
database update
fod.acknowledged event
frontend action
frontend state update
```

Validation:

```text
acknowledge action succeeds
database state changes
UI changes state
invalid detection handled
duplicate request handled deterministically
history remains correct
```

Then run all smoke and regression tests.

---

## Milestone 11: Error Recovery and Monitoring

Implement:

```text
camera reconnection
performance monitor
system status enrichment
controlled worker exception handling
warning events
```

Validation:

```text
camera disconnect detected
camera offline event emitted
reconnect attempted
camera recovery represented
inference does not process invalid frames
metrics remain valid
```

Then run the complete regression suite.

---

## Milestone 12: Final Prototype Validation

Run:

```text
backend tests
frontend tests
frontend type checking
frontend production build
smoke test
physical camera test
recorded-video test
model inference test
database persistence test
evidence save test
WebSocket alert test
acknowledgement test
camera recovery test
extended runtime stability test
```

Record results in:

```text
docs/VALIDATION_REPORT.md
```

---

# 40. Prototype Acceptance Criteria

The prototype is accepted when all of the following are true.

## Camera and Inference

```text
[ ] one camera can be opened
[ ] frames are continuously captured
[ ] supplied `model_weight.pt` is available
[ ] `model_weight.pt` can be exported to `model_weight.engine`
[ ] TensorRT engine loads successfully
[ ] real-time inference runs on the NVIDIA GPU
[ ] detections are normalized
[ ] annotated frames are generated
```

## Interface

```text
[ ] browser dashboard loads
[ ] live annotated feed is visible
[ ] camera status is visible
[ ] inference status is visible
[ ] basic performance measurements are visible
```

## Detection and Alerts

```text
[ ] confirmed detections generate alerts
[ ] alerts reach frontend in real time
[ ] evidence images are saved
[ ] detection metadata is persisted
[ ] detection history is accessible
[ ] operator can acknowledge alerts
```

## Reliability

```text
[ ] camera failure is visible
[ ] controlled camera recovery exists
[ ] worker exceptions are logged
[ ] application shuts down cleanly
[ ] no unbounded frame queue exists
```

## Quality

```text
[ ] smoke tests pass
[ ] validation tests pass
[ ] regression tests pass
[ ] frontend type check passes
[ ] frontend production build passes
[ ] final validation report exists
```

---

# 41. Mandatory Codex Implementation Rules

Codex must follow these rules throughout implementation.

### Rule 1

Do not redesign the architecture without an explicit specification change.

### Rule 2

Do not introduce multiple-camera support during the prototype stage.

### Rule 3

Do not put camera capture, inference, database writes, and network delivery into one sequential processing loop.

### Rule 4

Do not create an unbounded camera frame queue.

### Rule 5

Keep all detector-specific code behind `ModelAdapter`.

### Rule 6

Do not expose detector-framework result objects outside the inference layer.

### Rule 7

Do not run inference from HTTP route handlers.

### Rule 8

Do not open the camera from HTTP route handlers.

### Rule 9

Do not store image bytes directly in the prototype detection table.

### Rule 10

Do not silently ignore camera, model, database, or evidence-storage failures.

### Rule 11

Do not fabricate system metrics.

### Rule 12

After every implementation change:

```text
implement
    ↓
run relevant feature tests
    ↓
run smoke tests
    ↓
run validation tests
    ↓
run regression tests
    ↓
fix failures
    ↓
rerun tests
```

### Rule 13

Do not proceed to the next milestone while required tests are failing.

### Rule 14

Do not remove existing tests merely to make a new implementation pass.

### Rule 15

Update documentation when an API contract, configuration parameter, data model, or important runtime behavior changes.

### Rule 16

Treat `model_weight.pt` as the supplied source model artifact. Export and validate `model_weight.engine`, then use the TensorRT engine as the normal runtime inference model on the configured NVIDIA GPU. Do not silently fall back to CPU inference.

---

# 42. Final Prototype Architecture

The approved architecture for implementation is:

```text
Physical Camera
       │
       ▼
OpenCV CameraManager
       │
       ▼
LatestFrameBuffer
       │
       ▼
InferenceEngine
       │
       ▼
ModelAdapter
       │
       ▼
PostProcessor
       │
       ▼
TemporalValidator
       │
       ├─────────────────► Frame Renderer
       │                          │
       │                          ▼
       │                   HTTP Video Stream
       │
       ▼
AlertManager
       │
       ├─────────────────► EvidenceStore
       │
       ├─────────────────► DetectionRepository
       │
       └─────────────────► WebSocket Events
                                  │
                                  ▼
                          React Dashboard
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
                Live Feed     Active Alert    History
                                  │
                                  ▼
                             Acknowledge
                                  │
                                  ▼
                              REST API
                                  │
                                  ▼
                               SQLite
```

This architecture is the implementation baseline for the single-camera FOD detection prototype.
