from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"

    camera_source: str = "0"
    camera_reconnect_delay_seconds: float = 2.0

    model_source_path: Path = Path("backend/models/weights/model_weight.pt")
    model_engine_path: Path = Path("backend/models/weights/model_weight.engine")
    model_runtime: str = "tensorrt"
    model_device: str = "cuda:0"
    model_confidence_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    model_iou_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    model_image_size: int = Field(default=640, gt=0)

    temporal_validation_enabled: bool = True
    temporal_window_size: int = Field(default=5, gt=0)
    temporal_required_hits: int = Field(default=3, gt=0)
    temporal_match_iou: float = Field(default=0.30, ge=0.0, le=1.0)

    database_url: str = "sqlite:///./backend/data/fod.db"
    evidence_directory: Path = Path("./backend/data/detections")

    stream_jpeg_quality: int = Field(default=80, ge=1, le=100)
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
