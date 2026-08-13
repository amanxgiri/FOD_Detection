from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.config import PublicConfigResponse

router = APIRouter()


@router.get("/config", response_model=PublicConfigResponse)
def get_config() -> PublicConfigResponse:
    settings = get_settings()
    return PublicConfigResponse(
        app_env=settings.app_env,
        camera_source=settings.camera_source,
        camera_sources=settings.camera_sources,
        model_source_paths={
            camera_id: str(path)
            for camera_id, path in settings.model_source_paths.items()
        },
        model_engine_paths={
            camera_id: str(path)
            for camera_id, path in settings.model_engine_paths.items()
        },
        model_runtime=settings.model_runtime,
        model_device=settings.model_device,
        model_confidence_threshold=settings.model_confidence_threshold,
        model_iou_threshold=settings.model_iou_threshold,
        model_image_size=settings.model_image_size,
        inference_idle_backoff_seconds=settings.inference_idle_backoff_seconds,
        temporal_validation_enabled=settings.temporal_validation_enabled,
        stream_jpeg_quality=settings.stream_jpeg_quality,
    )
