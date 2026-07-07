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
