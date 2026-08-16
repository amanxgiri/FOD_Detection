from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.camera.opencv_capture import DEFAULT_FFMPEG_CAPTURE_OPTIONS


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"

    camera_source: str = "0"
    camera_1_source: str = "0"
    camera_2_source: str = "1"
    camera_3_source: str = "2"
    camera_reconnect_delay_seconds: float = 2.0
    camera_ffmpeg_capture_options: str = DEFAULT_FFMPEG_CAPTURE_OPTIONS
    camera_capture_open_timeout_ms: int = Field(default=5_000, gt=0)
    camera_capture_read_timeout_ms: int = Field(default=1_000, gt=0)
    camera_capture_buffer_size: int = Field(default=1, gt=0)
    camera_capture_decoder_threads: int = Field(default=1, gt=0)
    camera_max_count: int = Field(default=8, ge=1, le=32)
    camera_discovery_interval_seconds: float = Field(default=2.0, ge=0.25)
    mediamtx_api_url: str = "http://127.0.0.1:9997"
    mediamtx_rtsp_url: str = "rtsp://127.0.0.1:8554"

    model_source_path: Path = Path("backend/models/weights/model_weight.pt")
    model_engine_path: Path = Path("backend/models/weights/model_weight.engine")
    model_1_source_path: Path = Path("backend/models/weights/model_1.pt")
    model_2_source_path: Path = Path("backend/models/weights/model_2.pt")
    model_3_source_path: Path = Path("backend/models/weights/model_3.pt")
    model_1_engine_path: Path = Path("backend/models/weights/model_1.engine")
    model_2_engine_path: Path = Path("backend/models/weights/model_2.engine")
    model_3_engine_path: Path = Path("backend/models/weights/model_3.engine")
    model_catalog_directory: Path = Path("backend/models/weights")
    model_runtime: str = "tensorrt"
    model_device: str = "cuda:0"
    model_fallback_device: str = "cpu"
    model_confidence_threshold: float = Field(default=0.01, ge=0.0, le=1.0)
    model_iou_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    model_image_size: int = Field(default=640, gt=0)
    model_fod_class_id: int = Field(default=0, ge=0)
    inference_idle_backoff_seconds: float = Field(default=0.001, ge=0.0)

    @property
    def camera_sources(self) -> dict[str, str]:
        return {
            "camera_1": self.camera_1_source,
            "camera_2": self.camera_2_source,
            "camera_3": self.camera_3_source,
        }

    @property
    def model_engine_paths(self) -> dict[str, Path]:
        return {
            "camera_1": self.model_1_engine_path,
            "camera_2": self.model_2_engine_path,
            "camera_3": self.model_3_engine_path,
        }

    @property
    def model_source_paths(self) -> dict[str, Path]:
        return {
            "camera_1": self.model_1_source_path,
            "camera_2": self.model_2_source_path,
            "camera_3": self.model_3_source_path,
        }

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
