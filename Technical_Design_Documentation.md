## Technical Design and Implementation Specification

**Document Status:** Revised Technical Specification
**Project Type:** Three-Camera Round-Robin Real-Time FOD Detection Prototype
**Primary Purpose:** Implementation specification for Codex  
**Primary Backend Language:** Python  
**Frontend:** React + TypeScript  
**Architecture Status:** Approved prototype baseline

---

# 1. Project Overview

The purpose of this project is to build a prototype application that performs real-time Foreign Object Debris (FOD) detection from three independent camera feeds.

Each camera has its own independently trained object-detection model. The three models are intentionally distinct and their detections remain associated with their source camera and model.

The source model weights will be supplied to the project as three artifacts:

```text
model_1.pt
model_2.pt
model_3.pt
```

Each `.pt` file is a source artifact used to produce a corresponding TensorRT engine. The deployed runtime must use `model_1.engine`, `model_2.engine`, and `model_3.engine`. Each engine is permanently assigned to its matching camera. Portable `.pt` fallback is not part of the three-camera deployment runtime.

The prototype must:

1. capture frames continuously and independently from three cameras;
    
2. preserve all three feeds as separate views without stitching, panoramic composition, or pixel-level fusion;
    
3. run exactly one TensorRT engine inference at a time using a synchronized three-slot round-robin schedule;
    
4. route camera 1 to model 1 in slot 1, camera 2 to model 2 in slot 2, and camera 3 to model 3 in slot 3, then repeat;
    
5. post-process and optionally temporally validate each camera's detections independently;
    
6. display three independent annotated live feeds in a browser;
    
7. generate camera- and model-attributed real-time FOD alerts;
    
8. save confirmed detection metadata and evidence images with camera and model identity;
    
9. allow an operator to view and acknowledge alerts;
    
10. expose per-camera, per-model, and scheduler performance and system-health information.
    

This project is a **prototype**, not a production airport deployment.

The implementation must therefore remain modular and maintainable without introducing unnecessary production-scale infrastructure.

---

# 2. Prototype Scope

## 2.1 Included in Scope

The initial prototype includes:

- three physical cameras with independent capture workers and feeds;
    
- three distinct TensorRT engine models loaded and assigned one-to-one to the cameras;
    
- real-time frame capture;
    
- serialized, synchronized round-robin inference with only one active engine execution at any instant;

- inference of camera 1 frames numbered `1, 4, 7, ...`, camera 2 frames numbered `2, 5, 8, ...`, and camera 3 frames numbered `3, 6, 9, ...` within a shared synchronized frame-tick sequence;
    
- confidence filtering;
    
- bounding-box rendering;
    
- optional temporal detection validation;
    
- three separate annotated browser video streams;
    
- real-time FOD alert events;
    
- detection history;
    
- alert acknowledgement;
    
- evidence-image storage;
    
- SQLite metadata storage;
    
- per-camera health reporting;
    
- per-model and scheduler inference performance reporting;
    
- smoke tests;
    
- validation tests;
    
- regression testing after changes.
    

---

## 2.2 Explicitly Out of Scope

The following must not be implemented in the first prototype unless the specification is intentionally revised later:

- camera calibration workflows;
    
- image stitching;
    
- panoramic frame generation;
    
- multi-view image or detection fusion;
    
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
    
- ensemble voting or automatic cross-model consensus; the three inference paths remain independent;
    
- anomaly-detection models;
    
- automatic model retraining;
    
- remote model registry integration.
    

The repository architecture should allow future development, but Codex must not prematurely implement these capabilities. Three-camera capture and the round-robin scheduler are explicitly in scope; stitching and inference-result fusion are not.

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

## 4.1 Single Ownership of Each Camera

Only the camera subsystem may directly interact with the three camera devices.

The API layer, frontend, inference engine, and alert manager must never open their own camera connections.

Each camera must have exactly one owner. The required ownership mapping is one `CameraManager` and one bounded `LatestFrameBuffer` per camera. No manager or buffer may be shared across camera devices.

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

Instead, all camera capture workers and the shared inference scheduler must run independently.

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

> The scheduler must intentionally infer only one of the three synchronized feeds per frame tick. Each camera is inferred once every three ticks, while capture and raw-feed publication continue on every tick.

This is an architectural requirement for this project.

### 4.2.1 Synchronized Three-Slot Inference Schedule

Let `tick` be a monotonically increasing synchronized frame tick shared by the three capture streams. The inference slot is selected by:

```text
selected_camera = ((tick - 1) mod 3) + 1
```

The required schedule is:

| Synchronized tick | Camera 1 frame | Camera 2 frame | Camera 3 frame | Engine executed |
|---:|---|---|---|---|
| 1 | infer | skip | skip | `model_1.engine` |
| 2 | skip | infer | skip | `model_2.engine` |
| 3 | skip | skip | infer | `model_3.engine` |
| 4 | infer | skip | skip | `model_1.engine` |
| 5 | skip | infer | skip | `model_2.engine` |
| 6 | skip | skip | infer | `model_3.engine` |

Here, `skip` means no model inference for that camera frame. It does not mean capture, display, timestamping, or health monitoring stops. The scheduler repeats this three-slot cycle indefinitely.

The scheduler must serialize GPU execution with a single inference worker or an equivalent exclusive execution lock. It must never dispatch two engine calls concurrently. This removes the resource contention caused by simultaneous execution of all three models. It preserves the minimal execution latency of an individual engine call, but deliberately reduces each camera's inference cadence to one-third of the synchronized capture cadence. For a capture rate of `F` frames per second, each camera's nominal inference rate is `F / 3`, subject to engine execution time and synchronization overhead.

Camera synchronization must not allow an unbounded queue to accumulate. The synchronization layer may use bounded per-camera slots keyed by tick. If the selected camera's exact frame is unavailable after a configurable short deadline, the scheduler must record a missed slot and advance; it must not reuse a stale frame or block the other cameras indefinitely.

### 4.2.2 Independent Verification Semantics

The three cameras observe somewhat similar operational areas, and each feed is evaluated by a distinct model. This supplies three independent detection paths for operational comparison. Independence means:

- camera 1 frames are evaluated only by model 1;
- camera 2 frames are evaluated only by model 2;
- camera 3 frames are evaluated only by model 3;
- detections, confidence scores, temporal histories, metrics, alerts, and evidence retain their camera/model identity;
- a detection from one lane is never copied into or presented as a detection from another lane.

This revision does not define automated majority voting, score averaging, cross-camera tracking, or a fused verification decision. If later required, consensus logic must be added as a separate downstream component without changing the one-engine-at-a-time scheduler.

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

The adapter must support the TensorRT engine format used by all three deployed models.

The deployed engine paths are:

```text
backend/models/weights/model_1.engine
backend/models/weights/model_2.engine
backend/models/weights/model_3.engine
```

For an Ultralytics-compatible TensorRT runtime, implement:

```text
TensorRTModelAdapter
```

If a source model cannot be exported to a compatible TensorRT engine, deployment readiness must fail clearly. Any future runtime change requires an explicit specification revision while preserving the same adapter interface.

The rest of the system must receive normalized application-level detection objects and must not depend on raw detector-library result objects.

### 4.3.1 Three-Model TensorRT Deployment Path

The user will provide three distinct trained source models:

```text
backend/models/weights/model_1.pt
backend/models/weights/model_2.pt
backend/models/weights/model_3.pt
```

These `.pt` files are source artifacts. They are not the deployed inference format.

Each source model must be exported separately to its matching TensorRT engine. The permanent assignment is model 1 to camera 1, model 2 to camera 2, and model 3 to camera 3.

```text
model_N.pt
        │
        ▼
TensorRT export
        │
        ▼
model_N.engine
        │
        ▼
TensorRT runtime inference
        │
        ▼
NVIDIA GPU (serialized execution shared by all three engines)
```

The deployment inference pipeline uses:

```text
backend/models/weights/model_1.engine
backend/models/weights/model_2.engine
backend/models/weights/model_3.engine
```

Each `.pt` source model must be retained so its matching TensorRT engine can be regenerated when the target GPU, CUDA, TensorRT, model input configuration, or deployment environment changes. Production-like three-camera execution requires all three `.engine` files and does not silently fall back to `.pt` models.

The export process must be implemented as a separate script:

```text
scripts/export_tensorrt.py
```

The export script must:

- accept a source/output pair and export each of `model_1.pt`, `model_2.pt`, and `model_3.pt`;
- validate that an NVIDIA CUDA-capable GPU is available;
- export the model to TensorRT engine format;
- save the generated engines as `model_1.engine`, `model_2.engine`, and `model_3.engine`;
- report the export configuration;
- fail clearly when export cannot be completed;
- not silently fall back to CPU during TensorRT export.

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

The CUDA dependency set assumes an NVIDIA GPU and driver compatible with CUDA
12.x. If the deployment machine uses a different CUDA major version, the PyTorch
and TensorRT wheel lines in `backend/requirements.txt` must be adjusted before
installation. The three-camera deployment host must provide compatible CUDA and
TensorRT runtimes. A CPU-only dependency set may still be used for unit tests and
non-inference development, but it is not an operational fallback for the required
three-engine pipeline.

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

The user-supplied `model_1.pt`, `model_2.pt`, and `model_3.pt` files are retained
as source artifacts. Their corresponding `.engine` files are the required
deployment artifacts. TensorRT engines remain
hardware/runtime-specific and must be regenerated on the target deployment
machine when the GPU, driver, CUDA, TensorRT, input size, or model version
changes. Additional generated `.engine` files and intermediate `.onnx` files are
ignored by git.

After export, all three generated engines must be validated independently and then validated together under the serialized round-robin scheduler before integration into the live inference pipeline.

Validation must include:

```text
[ ] all three TensorRT engine files exist
[ ] each TensorRT engine loads successfully
[ ] inference runs on the NVIDIA GPU
[ ] known test image can be processed
[ ] output detections can be normalized
[ ] output shape and class mapping are correct
[ ] no unexpected numerical or detection-format regression is introduced
[ ] inference latency is measured
[ ] each engine remains permanently mapped to its assigned camera
[ ] the scheduler never overlaps engine executions
[ ] the repeating slot order is camera 1, camera 2, camera 3
```

The deployment runtime must use strict TensorRT mode. Startup succeeds only when
all three engine files load and warm up successfully. A missing or incompatible
engine is a visible model-path failure; the application must not silently replace
it with a `.pt` model because doing so would invalidate latency and scheduling
assumptions.

During backend startup, each configured `.pt`/`.engine` pair must be checked
before the camera runtime begins. If a source `.pt` exists and its corresponding
engine does not, the backend must export that model to the configured TensorRT
engine path automatically. It must never overwrite an existing engine. Export
failure must stop startup with the affected camera/model identity in the error.

---

## 4.4 Critical Configuration Must Not Be Hard-Coded

The following must be configurable:

- all three camera sources and their stable camera IDs;
    
- all three engine paths and their fixed camera-to-model assignments;

- synchronization tolerance and inference-slot deadline;
    
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

The target inference hardware is an NVIDIA CUDA-capable GPU. The three supplied source models must be exported to three TensorRT engine artifacts and validated on the target host.

The three-camera runtime is strict TensorRT. All engines may remain loaded, but a shared scheduler permits only one engine execution at a time. This avoids concurrent GPU contention while maintaining independent model outputs.

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

The system contains three independent capture and processing lanes coordinated by one serialized inference scheduler:

```text
Camera 1 --> Buffer 1 --\
Camera 2 --> Buffer 2 ----> RoundRobinInferenceScheduler --> one engine call at a time
Camera 3 --> Buffer 3 --/             |
                                      +--> slot 1: Model 1 + Camera 1
                                      +--> slot 2: Model 2 + Camera 2
                                      +--> slot 3: Model 3 + Camera 3
                                                   |
                                                   v
                              Per-camera results, annotations, alerts, and streams
```

There is no image stitching or panoramic composition. The detailed pipeline diagram below represents one selected camera/model lane; that lane is instantiated three times, while its `InferenceEngine` entry is controlled by the shared scheduler.

```text
                    SELECTED CAMERA LANE (ONE OF THREE)
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
1. All three CameraManager instances capture their current frames independently.
2. Each frame receives a camera ID, per-camera sequence number, synchronized tick, and timestamp.
3. Each camera's bounded LatestFrameBuffer replaces its previous frame.
4. RoundRobinInferenceScheduler selects the camera for the current tick.
5. Non-selected camera frames remain available for live display but skip inference.
6. The scheduler invokes only the ModelAdapter permanently assigned to the selected camera.
7. The selected TensorRT engine performs prediction under exclusive GPU execution ownership.
8. Model output is normalized and tagged with camera ID, model ID, tick, and source sequence number.
9. The selected camera's PostProcessor and independent TemporalValidator state are updated.
10. Bounding boxes are rendered on that camera's selected frame; skipped frames may retain the latest valid overlay with its inference age clearly tracked.
11. The corresponding latest annotated frame becomes available to that camera's stream endpoint.
12. Per-camera, per-model, and scheduler metrics are updated.
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

For the revised architecture, `backend/models/weights/` contains the three source `.pt` files and the three required `.engine` files. The inference package additionally contains a dedicated round-robin scheduler module, and the frontend component tree includes `LiveCameraGrid.tsx`. These additions supersede the single illustrative weight entry in the tree above.

---

# 9. Backend Application Lifecycle

Application startup and shutdown must be controlled through FastAPI lifespan handling. FastAPI documents the `lifespan` mechanism for startup and shutdown logic.

## 9.1 Startup Order

The required startup order is:

```text
1. Load configuration
2. Configure logging
3. Initialize database
4. Initialize the three-camera runtime and synchronization clock
5. Initialize all three cameras
6. Validate all camera connections where possible
7. Start three independent capture workers
8. Initialize WebSocket manager
9. Mark system ready with inference stopped
10. On operator Start Inference command, load all three configured TensorRT engines
11. Validate the fixed camera-to-engine mapping
12. Warm up each engine sequentially under exclusive GPU ownership
13. Start the single round-robin inference scheduler after all engine warmups succeed
```

The health endpoint must not report the system as fully ready before all critical components have initialized.

---

## 9.2 Shutdown Order

Required shutdown:

```text
1. Mark system as shutting down
2. Stop accepting new long-running operations
3. Stop the round-robin inference scheduler
4. Stop all camera workers
5. Release all three cameras
6. Close all three model resources where required
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

Three `CameraManager` instances must be created from configuration, one per physical camera. Each instance owns only its assigned device and publishes only to its assigned buffer.

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
    camera_id: str
    sequence_id: int
    synchronized_tick: int
    captured_at: datetime
    frame: np.ndarray
```

The raw frame object should not be exposed to the frontend or serialized through REST.

---

## 10.4 Camera Source Configuration

The source must be configurable.

Example:

```env
CAMERA_1_SOURCE=0
CAMERA_2_SOURCE=1
CAMERA_3_SOURCE=2
```

The implementation should also support a local video file as an alternate input source for development and repeatable testing.

OpenCV's `VideoCapture` interface accepts camera devices and video sources, which supports this testability requirement.

Example:

```env
CAMERA_1_SOURCE=backend/tests/fixtures/camera_1.mp4
CAMERA_2_SOURCE=backend/tests/fixtures/camera_2.mp4
CAMERA_3_SOURCE=backend/tests/fixtures/camera_3.mp4
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

One latest-frame buffer per camera is required. Together, the three buffers form the bounded input set read by the round-robin scheduler.

It must:

- be bounded;
    
- store only the newest required frame state;
    
- be thread-safe;
    
- allow the scheduler to retrieve the selected camera's frame for a synchronized tick or report that the slot was missed;
    
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

Define a model-independent interface. Create three adapter instances, each loaded from a different TensorRT engine and permanently registered to one camera ID. Adapter selection is made only by the scheduler mapping; detections from one adapter must never be attributed to another camera.

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
    camera_id: str
    model_id: str
    synchronized_tick: int
    source_sequence_id: int
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

# 13. Round-Robin Inference Engine

File:

```text
backend/app/inference/inference_engine.py
```

## Responsibilities

The inference engine and scheduler must:

1. advance through the repeating camera slots `1, 2, 3` using the synchronized tick;
    
2. retrieve the selected camera's current frame and record a missed slot when it is unavailable;
    
3. call only the model adapter assigned to the selected camera;
    
4. guarantee that no second model call begins until the current call completes;
    
5. measure execution latency, scheduler wait, slot misses, and result age;
    
6. send results to the selected camera's post-processing and temporal-validation state;
    
7. update only the selected camera's annotated-frame store and latest result;
    
8. update aggregate and per-camera/per-model performance metrics.
    

Conceptual interface:

```python
class RoundRobinInferenceScheduler:
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def is_running(self) -> bool:
        ...

    def _scheduler_loop(self) -> None:
        ...
```

The scheduler owns the right to execute inference. Camera workers, renderers, API handlers, and stream handlers must never call a model directly. Models may remain loaded between slots to avoid repeated initialization overhead.

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
    camera_id: str
    model_id: str
    synchronized_tick: int
    source_sequence_id: int
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

The temporal validator will allow detections to be confirmed from repeated observations across a configurable recent-inference window. Each camera/model pair must have isolated temporal state; detections from different cameras or models must never be merged into one temporal candidate.

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

- identify the source camera and inference age;
    
- produce a frame ready for JPEG encoding.
    

Do not mutate the original raw camera frame in the camera buffer.

Each camera has its own annotated-frame store. On frames that do not receive an inference slot, the UI may display the current raw frame with the most recent valid overlay only if it also exposes the overlay age; it must not imply that the skipped frame itself was inferred.

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

- preserve `camera_id`, `model_id`, synchronized tick, and source sequence ID in every alert and record;
    
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
camera_id
model_id
synchronized_tick
source_sequence_id
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
  "cameras": {"camera_1": "online", "camera_2": "online", "camera_3": "online"},
  "models": {"model_1": "loaded", "model_2": "loaded", "model_3": "loaded"},
  "inference_scheduler": "running"
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
  "camera_statuses": {"camera_1": "online", "camera_2": "online", "camera_3": "online"},
  "model_statuses": {"model_1": "loaded", "model_2": "loaded", "model_3": "loaded"},
  "inference_status": "running",
  "active_slot": 2,
  "active_camera_id": "camera_2",
  "capture_fps": {"camera_1": 30.0, "camera_2": 30.0, "camera_3": 30.0},
  "inference_fps": {"camera_1": 10.0, "camera_2": 10.0, "camera_3": 10.0},
  "average_inference_ms": 36.8,
  "latest_frame_age_ms": {"camera_1": 41, "camera_2": 38, "camera_3": 45},
  "scheduler_missed_slots": 0,
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
      "camera_id": "camera_2",
      "model_id": "model_2",
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

Engine paths, camera-to-model assignments, synchronization settings, database path, and camera device ownership settings must not be changed while the pipeline is running.

---

# 22. Video Streaming

Endpoint:

```http
GET /api/v1/cameras/{camera_id}/stream
```

Implement each of the three independent live annotated feeds as its own HTTP streaming response using a multipart frame stream. No endpoint may stitch or combine camera pixels.

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

Each video endpoint must consume only the latest annotated frame belonging to its requested camera ID.

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
    "camera_id": "camera_2",
    "model_id": "model_2",
    "synchronized_tick": 125,
    "source_sequence_id": 125,
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

The first version must prioritize one main operator dashboard containing three clearly identified, independent camera panels.

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

## 25.1 LiveCameraGrid and LiveCamera Components

File:

```text
frontend/src/components/LiveCamera.tsx
frontend/src/components/LiveCameraGrid.tsx
```

Responsibilities:

- render one reusable `LiveCamera` instance for each of the three camera IDs;

- display each camera's independent backend stream without stitching;
    
- show offline placeholder when unavailable;
    
- display connection state;

- display camera ID, assigned model ID, last inference tick, and inference age;
    
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
Assigned model
Round-robin slot state
Inference scheduler
Backend connection
WebSocket connection
```

---

## 25.5 PerformanceMetrics

Display available measured metrics:

```text
Capture FPS
Per-camera inference FPS
Per-model average inference latency
Latest frame age
Latest inference age
Missed scheduler slots
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

CAMERA_1_SOURCE=0
CAMERA_2_SOURCE=1
CAMERA_3_SOURCE=2
CAMERA_RECONNECT_DELAY_SECONDS=2

MODEL_1_ENGINE_PATH=backend/models/weights/model_1.engine
MODEL_2_ENGINE_PATH=backend/models/weights/model_2.engine
MODEL_3_ENGINE_PATH=backend/models/weights/model_3.engine
MODEL_RUNTIME=tensorrt
MODEL_DEVICE=cuda:0
MODEL_CONFIDENCE_THRESHOLD=0.01
MODEL_IOU_THRESHOLD=0.50
MODEL_IMAGE_SIZE=640
INFERENCE_SCHEDULE=round_robin
INFERENCE_SLOT_COUNT=3
INFERENCE_SLOT_DEADLINE_MS=50
CAMERA_SYNC_TOLERANCE_MS=20

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

The initial backend should use one FastAPI process, three capture workers, and one serialized inference scheduler. The scheduler is the only component authorized to execute any of the three loaded engines.

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

- three physical cameras;
    
- three loaded TensorRT engines with one active execution at a time;
    
- three bounded latest-frame buffers;
    
- one scheduler coordinating three independent inference lanes.
    

Do not start several backend worker processes that each attempt to initialize the complete camera and model pipeline.

Horizontal scaling is outside prototype scope.

---

# 29. Thread Safety Requirements

Shared mutable runtime state must be protected.

The following require safe synchronization:

- latest raw frame;

- synchronized tick and scheduler slot state;
    
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
inference_fps_by_camera
last_inference_ms_by_model
average_inference_ms_by_model
frames_captured
frames_inferred
frames_skipped
scheduled_slots_by_camera
missed_slots_by_camera
last_inference_tick_by_camera
inference_result_age_ms_by_camera
confirmed_detection_count
latest_frame_timestamp
camera_read_failures_by_camera
```

Use a rolling or bounded measurement approach.

Do not retain unlimited latency samples in memory.

Intentional non-selected frames must be counted separately from error-driven drops or missed scheduler slots. Dashboard latency must distinguish engine execution latency from end-to-end inference-result age. A low engine execution time does not imply that every captured frame was inferred.

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

Temporary failure of one camera must not terminate the API application or stop capture on the other cameras. The failed camera's scheduled inference slots must be recorded as missed and skipped until it recovers; its engine must not be fed a frame from another camera.

Windows OpenCV/MSMF read failures, including `OnReadSample` or `can't grab
frame` logs after the camera reports opened, must follow this same path. They
should be surfaced as camera degraded/offline status and diagnosed with
`scripts/check_camera.py` against the exact configured source.

---

## 32.2 Model Load Failure

If any of the three required TensorRT engines cannot load:

- application readiness must be false;
    
- error must be logged clearly;
    
- the round-robin inference scheduler must not start;
    
- health information must identify the failed engine and assigned camera.
    

The application must not silently fall back to a `.pt` model or continue while pretending that the complete three-model inference schedule is operational.

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
[ ] all three `.pt` source models are accessible for export
[ ] TensorRT export script can validate export prerequisites for each model
[ ] `model_1.engine`, `model_2.engine`, and `model_3.engine` are accessible
[ ] all three TensorRT engines load on the target NVIDIA deployment
[ ] runtime fails clearly rather than falling back when any engine cannot load
[ ] all three camera sources open
[ ] frames can be captured and synchronized from all three cameras
[ ] each engine can run on a known frame from its assigned camera
[ ] the six-tick round-robin pattern matches `1, 2, 3, 1, 2, 3`
[ ] instrumentation proves there are no overlapping engine calls
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
all three cameras open
frames arrive independently from all cameras
per-camera sequence IDs increase
synchronized ticks and timestamps exist
each buffer exposes only its camera's latest frame
all cameras release cleanly
three test video sources work together
```

Then run all smoke and regression tests.

---

## Milestone 3: Model Integration

Implement:

```text
ModelAdapter
model loader
TensorRT export script
three `.pt` source-model artifacts
`model_1.engine`, `model_2.engine`, and `model_3.engine` generation
TensorRT runtime adapter
three strict TensorRT adapter instances
NVIDIA GPU inference configuration
one-frame inference for each engine/camera assignment
normalized detections
model diagnostic script
```

Validation:

```text
all three source models are accessible
TensorRT export completes successfully for every model
all three engine files are created
all three TensorRT engines load successfully
inference runs on the configured NVIDIA GPU where available
startup fails visibly if any required engine is unavailable
each engine processes a known frame from its assigned camera
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
three camera workers
three latest-frame buffers
round-robin inference scheduler
post-processing
performance timing
```

Validation:

```text
capture continues independently on all three cameras
each camera is inferred once every three synchronized ticks
only one engine executes at a time
camera-to-model assignments remain fixed
missed slots advance without stale-frame reuse or unbounded waiting
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
three latest annotated frame stores
JPEG encoding
three camera-specific HTTP video streams
```

Validation:

```text
browser receives all three independent streams
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
[ ] all three cameras can be opened
[ ] frames are continuously and independently captured from all cameras
[ ] all three supplied source models are available
[ ] each source model can be exported to its corresponding TensorRT engine
[ ] all three TensorRT engines load successfully on the target NVIDIA deployment
[ ] deployment runtime is engine-only and reports any missing engine clearly
[ ] inference follows the synchronized repeating camera order `1, 2, 3`
[ ] only one model executes at any instant
[ ] each camera receives inference once every three synchronized frame ticks
[ ] detections are normalized
[ ] annotated frames are generated
```

## Interface

```text
[ ] browser dashboard loads
[ ] three separate live annotated feeds are visible without stitching
[ ] all three camera statuses and model assignments are visible
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

Implement exactly three camera lanes and the specified round-robin inference schedule. Do not add stitching, multi-view fusion, cross-camera tracking, or concurrent engine execution.

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

Treat the three `.pt` files as distinct source artifacts. Export and validate `model_1.engine`, `model_2.engine`, and `model_3.engine` on the target NVIDIA GPU. Deployment must use strict TensorRT mode, preserve the fixed camera-to-engine mapping, and fail clearly if any engine cannot run.

---

# 42. Final Prototype Architecture

The approved architecture for implementation is:

```text
Camera 1 --> LatestFrameBuffer 1 --> ModelAdapter 1 (`model_1.engine`) --\
Camera 2 --> LatestFrameBuffer 2 --> ModelAdapter 2 (`model_2.engine`) ----> independent results
Camera 3 --> LatestFrameBuffer 3 --> ModelAdapter 3 (`model_3.engine`) --/
                   ^                         ^
                   |                         |
       synchronized frame ticks    RoundRobinInferenceScheduler
                                   slots: 1 --> 2 --> 3 --> repeat
                                   maximum concurrent inference calls: 1

Independent results --> per-camera post-processing and temporal validation
                    --> per-camera annotated streams (no stitching)
                    --> camera/model-attributed alerts, evidence, and history
```

The following linear view represents the downstream processing path for the camera/model lane selected in the current scheduler slot:

```text
Selected Physical Camera (1 of 3)
       │
       ▼
Assigned OpenCV CameraManager
       │
       ▼
Assigned LatestFrameBuffer
       │
       ▼
RoundRobinInferenceScheduler
       │
       ▼
Assigned TensorRT ModelAdapter
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
                Live Feeds    Active Alert    History
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

This architecture is the implementation baseline for the three-camera, three-model, serialized round-robin FOD detection prototype.
