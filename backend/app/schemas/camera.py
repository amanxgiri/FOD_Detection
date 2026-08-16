from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class CameraResponse(BaseModel):
    id: str
    display_name: str
    hostname: str
    rtsp_path: str
    publisher_ip: str | None
    stream_status: str
    selected_model_id: str | None
    model_status: str
    latency_status: str
    latency_message: str | None = None
    discovered_at: datetime
    last_seen_at: datetime


class CameraListResponse(BaseModel):
    items: list[CameraResponse]
    max_cameras: int
    discovery_status: str
    warning: str | None = None


class CameraUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)


class CameraCreateRequest(BaseModel):
    source: str | None = Field(default=None, min_length=1, max_length=2048)
    # Retained so older frontend builds and API clients continue to work.
    rtsp_url: str | None = Field(default=None, min_length=1, max_length=2048)

    @model_validator(mode="after")
    def require_one_source(self) -> "CameraCreateRequest":
        if self.source is None and self.rtsp_url is None:
            raise ValueError("source is required")
        if self.source is not None and self.rtsp_url is not None:
            raise ValueError("provide source or rtsp_url, not both")
        return self


class CameraModelRequest(BaseModel):
    model_id: str | None = Field(default=None, max_length=128)


class ModelResponse(BaseModel):
    id: str
    display_name: str
    status: str = "ready"


class ModelListResponse(BaseModel):
    items: list[ModelResponse]
