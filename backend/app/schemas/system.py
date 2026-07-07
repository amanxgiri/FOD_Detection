from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    ready: bool
    camera: str
    model: str
    inference_worker: str


class SystemStatusResponse(BaseModel):
    camera_status: str
    model_status: str
    inference_status: str
    backend_status: str
    websocket_status: str
    capture_fps: float
    inference_fps: float
    average_inference_ms: float
    latest_frame_age_ms: int | None
    total_confirmed_detections: int
