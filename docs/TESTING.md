# Testing

Every milestone must run feature-specific tests, smoke tests, validation tests,
and relevant regression tests before moving to the next milestone.

Milestone 2 camera capture can be validated without a physical camera by using
`backend/tests/fixtures/test_runway.avi` with `scripts/check_camera.py`.

Milestone 3 source-model validation can be run with `scripts/check_model.py`.
`scripts/export_tensorrt.py --check-prerequisites-only` should fail clearly on
machines without CUDA/TensorRT prerequisites.

Milestone 4 inference-worker behavior is validated with a fake model adapter so
frame skipping, worker error handling, post-processing, and metrics can be tested
without requiring a TensorRT engine.

Milestone 5 streaming checks use `frame_limit=1` to validate the MJPEG response
without leaving an infinite test stream open.

Milestone 6 dashboard validation includes backend `/api/v1/system/status`,
frontend type checking, and frontend production build.

Milestone 7 persistence validation uses temporary SQLite databases and evidence
directories for repository and API tests. The smoke test now verifies the
detection history endpoint initializes successfully.

Milestone 8 temporal validation tests cover persistent, intermittent, isolated,
spatially separate, expired, and disabled-validation cases.

Milestone 9 WebSocket alert validation checks event schema, connection cleanup,
broadcast delivery, frontend type checking, and the smoke-test connection path.

Milestone 10 acknowledgement validation checks REST status updates,
deterministic repeated acknowledgement, `fod.acknowledged` event schema, and
frontend acknowledgement state.

Milestone 11 recovery tests cover camera disconnect/reconnect transitions,
invalid-frame handling, system status derivation, and warning-event delivery.

Live prototype validation includes a lifespan test that starts a fake camera,
publishes frames to the MJPEG stream, and verifies clean shutdown. CORS coverage
also includes the Vite loopback origin `http://127.0.0.1:5173`.
