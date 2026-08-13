from pydantic import BaseModel


class PublicConfigResponse(BaseModel):
    app_env: str
    camera_source: str
    camera_sources: dict[str, str]
    model_source_paths: dict[str, str]
    model_engine_paths: dict[str, str]
    model_runtime: str
    model_device: str
    model_confidence_threshold: float
    model_iou_threshold: float
    model_image_size: int
    inference_slot_timeout_seconds: float
    temporal_validation_enabled: bool
    stream_jpeg_quality: int
