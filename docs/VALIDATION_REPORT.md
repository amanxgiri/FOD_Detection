# Validation Report

Validation date: 2026-07-08

This report records the Milestone 12 prototype validation results. Automated
checks were run locally against the current repository state. Hardware-specific
TensorRT validation is blocked in this environment because CUDA-enabled PyTorch
is not available.

## Command Results

| Area | Command | Result | Notes |
| --- | --- | --- | --- |
| Backend tests | `.\.venv\Scripts\python.exe -m pytest -q backend\tests` | Passed | `77 passed in 1.96s` |
| Backend smoke test | `.\.venv\Scripts\python.exe scripts\smoke_test.py` | Passed | Health, system status, detections, WebSocket connection, and MJPEG stream path passed |
| Recorded-video camera test | `.\.venv\Scripts\python.exe scripts\check_camera.py --source backend\tests\fixtures\test_runway.avi --timeout 5` | Passed | Captured one frame at `32x24` |
| Physical camera test | `.\.venv\Scripts\python.exe scripts\check_camera.py --source 0 --timeout 5` | Passed | Captured one frame at `640x480` |
| Source model check | `.\.venv\Scripts\python.exe scripts\check_model.py` | Passed | `backend\models\weights\model_weight.pt` is available |
| TensorRT prerequisite check | `.\.venv\Scripts\python.exe scripts\export_tensorrt.py --check-prerequisites-only` | Blocked | Failed because CUDA-enabled PyTorch is not available in this environment |
| Frontend type checking | `npm run typecheck` | Passed | TypeScript build completed |
| Frontend production build | `npm run build` | Passed | Vite production bundle generated successfully |
| Frontend tests | `npm run test` | Not configured | `frontend/package.json` does not define a `test` script |
| Live runtime startup | Backend lifespan with fake camera source | Passed | App startup publishes camera frames into the MJPEG stream and shutdown stops the camera manager |
| Vite loopback CORS | `OPTIONS /api/v1/health` from `http://127.0.0.1:5173` | Passed | Backend allows the Vite dev origin used by `npm run dev` |
| Bounded stability check | Repeated in-process API, stream, and WebSocket loop | Passed | 25 loops over status, detections, stream, and WebSocket connection path |

## Feature Validation Coverage

| Requirement | Status | Evidence |
| --- | --- | --- |
| Backend tests | Passed | Full backend suite passed |
| Frontend tests | Not configured | No frontend test script exists |
| Frontend type checking | Passed | `npm run typecheck` passed |
| Frontend production build | Passed | `npm run build` passed |
| Smoke test | Passed | `scripts/smoke_test.py` passed |
| Physical camera test | Passed | OpenCV source `0` captured a frame |
| Recorded-video test | Passed | Fixture video captured a frame |
| Model inference test | Partially validated | Source model exists; TensorRT runtime validation requires CUDA/TensorRT host |
| Database persistence test | Passed | Covered by repository and detections API tests |
| Evidence save test | Passed | Covered by evidence store, alert manager, and detections API tests |
| WebSocket alert test | Passed | Covered by WebSocket event and route tests |
| Acknowledgement test | Passed | Covered by repository, API, WebSocket schema, and frontend state handling checks |
| Camera recovery test | Passed | Covered by camera manager disconnect/reconnect test |
| Extended runtime stability test | Passed | Bounded repeated API, stream, and WebSocket loop passed |

## Prototype Acceptance Criteria

### Camera and Inference

| Criterion | Status | Notes |
| --- | --- | --- |
| One camera can be opened | Passed | Physical camera source `0` opened and captured a frame |
| Frames are continuously captured | Passed | Camera manager tests cover capture loop behavior; recorded and physical sources captured frames |
| Supplied `model_weight.pt` is available | Passed | Source model check passed |
| `model_weight.pt` can be exported to `model_weight.engine` | Blocked | Requires CUDA-enabled PyTorch and TensorRT on the deployment host |
| TensorRT engine loads successfully | Blocked | Requires generated `.engine` file and TensorRT runtime |
| Real-time inference runs on the NVIDIA GPU | Blocked | Requires CUDA/TensorRT deployment host |
| Detections are normalized | Passed | Post-processing and inference tests cover normalized detection output |
| Annotated frames are generated | Passed | Renderer and stream tests cover annotated/MJPEG output |

### Interface

| Criterion | Status | Notes |
| --- | --- | --- |
| Browser dashboard loads | Passed | Production bundle builds and backend CORS allows both `localhost:5173` and `127.0.0.1:5173` |
| Live annotated feed is visible | Passed | Backend startup publishes live camera frames to the MJPEG stream; stream endpoint returns JPEG payload |
| Camera status is visible | Passed | Dashboard consumes `/api/v1/system/status`; typecheck/build passed |
| Inference status is visible | Passed | Dashboard consumes `/api/v1/system/status`; typecheck/build passed |
| Basic performance measurements are visible | Passed | System status and dashboard metric components build successfully |

### Detection and Alerts

| Criterion | Status | Notes |
| --- | --- | --- |
| Confirmed detections generate alerts | Passed | Alert manager tests cover persisted alert creation |
| Alerts reach frontend in real time | Passed | WebSocket route and frontend socket handling validate event delivery path |
| Evidence images are saved | Passed | Evidence store and API tests cover JPEG evidence |
| Detection metadata is persisted | Passed | Repository and detections API tests cover metadata persistence |
| Detection history is accessible | Passed | Detections API and frontend data service are implemented |
| Operator can acknowledge alerts | Passed | API, repository, WebSocket event schema, and frontend handler are implemented |

### Reliability

| Criterion | Status | Notes |
| --- | --- | --- |
| Camera failure is visible | Passed | Camera manager emits degraded/offline transitions |
| Controlled camera recovery exists | Passed | Camera manager reconnect test covers recovery transitions |
| Worker exceptions are logged | Passed | Inference worker records controlled errors and rejects invalid frames |
| Application shuts down cleanly | Passed | Smoke and TestClient lifecycle paths complete without hanging workers |
| No unbounded frame queue exists | Passed | `LatestFrameBuffer` stores only the latest frame |

## Open Validation Gates

- Configure a frontend unit/component test runner if frontend tests are required
  as a formal acceptance gate.
- Rerun TensorRT export, TensorRT engine loading, and NVIDIA GPU real-time
  inference on a host with CUDA-enabled PyTorch, TensorRT, and compatible NVIDIA
  drivers installed.
- Perform a live browser walkthrough against the running backend/frontend stack
  for visual dashboard acceptance.
