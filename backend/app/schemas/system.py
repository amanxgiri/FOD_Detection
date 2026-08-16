from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    ready: bool
    camera: str
    model: str
    inference_worker: str


class SystemStatusResponse(BaseModel):
    camera_status: str
    camera_statuses: dict[str, str]
    model_status: str
    model_statuses: dict[str, str]
    inference_status: str
    active_camera_id: str | None = None
    scheduler_slot_count: int = 0
    scheduler_missed_slots: int = 0
    backend_status: str
    websocket_status: str
    capture_fps: float
    inference_fps: float
    average_inference_ms: float
    latest_frame_age_ms: int | None
    capture_to_host_ms: float | None
    average_capture_to_host_ms: float | None
    source_timestamp_frames: int
    capture_to_host_ms_by_camera: dict[str, float | None]
    average_capture_to_host_ms_by_camera: dict[str, float | None]
    source_timestamp_frames_by_camera: dict[str, int]
    inference_ms_by_camera: dict[str, float | None]
    average_inference_ms_by_camera: dict[str, float | None]
    total_latency_ms_by_camera: dict[str, float | None]
    average_total_latency_ms_by_camera: dict[str, float | None]
    total_confirmed_detections: int
