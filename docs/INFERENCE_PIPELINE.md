# Inference Pipeline

Inference is specified for a TensorRT runtime engine generated from
`backend/models/weights/model_weight.pt`. The implementation starts in Milestone 3.

Milestone 3 adds the model adapter interface, normalized `RawDetection` type,
TensorRT adapter prerequisite checks, and export/diagnostic scripts. Actual engine
generation must be run on a CUDA/TensorRT-capable machine and must not fall back to CPU.
