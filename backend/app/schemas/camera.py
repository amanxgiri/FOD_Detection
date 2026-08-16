from datetime import datetime

from pydantic import BaseModel, Field


class CameraResponse(BaseModel):
    id: str
    display_name: str
    hostname: str
    rtsp_path: str
    publisher_ip: str | None
    stream_status: str
    selected_model_id: str | None
    model_status: str
    discovered_at: datetime
    last_seen_at: datetime


class CameraListResponse(BaseModel):
    items: list[CameraResponse]
    max_cameras: int
    discovery_status: str
    warning: str | None = None


class CameraUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)


class CameraModelRequest(BaseModel):
    model_id: str | None = Field(default=None, max_length=128)


class ModelResponse(BaseModel):
    id: str
    display_name: str
    status: str = "ready"


class ModelListResponse(BaseModel):
    items: list[ModelResponse]
