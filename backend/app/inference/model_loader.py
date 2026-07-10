from pathlib import Path

from app.core.config import Settings
from app.core.paths import resolve_project_path
from app.inference.model_adapter import (
    ModelAdapter,
    ModelArtifactNotFoundError,
    ModelIntegrationError,
    TensorRTModelAdapter,
)


def validate_source_model(path: Path) -> None:
    path = resolve_project_path(path)
    if not path.exists():
        raise ModelArtifactNotFoundError(f"source model not found: {path}")
    if path.suffix.lower() != ".pt":
        raise ModelIntegrationError(f"source model must be a .pt file: {path}")


def validate_engine_model(path: Path) -> None:
    path = resolve_project_path(path)
    if not path.exists():
        raise ModelArtifactNotFoundError(f"TensorRT engine not found: {path}")
    if path.suffix.lower() != ".engine":
        raise ModelIntegrationError(f"TensorRT engine must be a .engine file: {path}")


def create_model_adapter(settings: Settings) -> ModelAdapter:
    runtime = settings.model_runtime.lower()
    if runtime == "tensorrt":
        return TensorRTModelAdapter(
            engine_path=settings.model_engine_path,
            device=settings.model_device,
            image_size=settings.model_image_size,
            confidence_threshold=settings.model_confidence_threshold,
            iou_threshold=settings.model_iou_threshold,
        )
    raise ModelIntegrationError(f"unsupported model runtime: {settings.model_runtime}")
