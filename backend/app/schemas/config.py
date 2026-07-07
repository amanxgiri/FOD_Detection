from pydantic import BaseModel


class PublicConfigResponse(BaseModel):
    app_env: str
    camera_source: str
    model_runtime: str
    model_device: str
    model_confidence_threshold: float
    model_iou_threshold: float
    model_image_size: int
    temporal_validation_enabled: bool
    stream_jpeg_quality: int
