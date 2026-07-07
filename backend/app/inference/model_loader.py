from pathlib import Path

from app.core.config import Settings
from app.inference.model_adapter import (
    ModelAdapter,
    ModelArtifactNotFoundError,
    ModelIntegrationError,
    TensorRTModelAdapter,
)


def validate_source_model(path: Path) -> None:
    if not path.exists():
        raise ModelArtifactNotFoundError(f"source model not found: {path}")
    if path.suffix.lower() != ".pt":
        raise ModelIntegrationError(f"source model must be a .pt file: {path}")


def validate_engine_model(path: Path) -> None:
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
        )
    raise ModelIntegrationError(f"unsupported model runtime: {settings.model_runtime}")
