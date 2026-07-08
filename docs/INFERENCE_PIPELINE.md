# Inference Pipeline

Inference is specified for a TensorRT runtime engine generated from
`backend/models/weights/model_weight.pt`. The implementation starts in Milestone 3.

Milestone 3 adds the model adapter interface, normalized `RawDetection` type,
TensorRT adapter prerequisite checks, and export/diagnostic scripts. Actual engine
generation must be run on a CUDA/TensorRT-capable machine and must not fall back to CPU.

Milestone 4 adds the decoupled inference worker. It waits on `LatestFrameBuffer`,
processes only newer sequence IDs, counts skipped frames, applies deterministic
post-processing, and records bounded performance metrics.

Milestone 5 adds annotation rendering and MJPEG streaming. The stream endpoint
only reads `LatestAnnotatedFrameStore`; it does not run inference from the route.

Milestone 8 adds temporal validation. The inference worker keeps post-processed
detections for rendering and exposes newly confirmed detections separately for
later alert generation.

Milestone 11 enriches runtime monitoring: camera status transitions can publish
state changes, inference rejects invalid frames before model execution, and
system status derives from live runtime managers when present.

Runtime controls keep inference off by default. The dashboard Start Inference
command loads and warms the configured model adapter before starting the worker;
Stop Inference stops the worker and unloads the adapter.
