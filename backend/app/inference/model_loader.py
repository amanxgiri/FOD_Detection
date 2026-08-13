from pathlib import Path

from app.core.config import Settings
from app.core.paths import resolve_project_path
from app.inference.model_adapter import (
    AutoFallbackModelAdapter,
    ModelAdapter,
    ModelArtifactNotFoundError,
    ModelIntegrationError,
    TensorRTModelAdapter,
    UltralyticsPtModelAdapter,
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
    tensorrt_adapter = TensorRTModelAdapter(
        engine_path=settings.model_engine_path,
        device=settings.model_device,
        image_size=settings.model_image_size,
        confidence_threshold=settings.model_confidence_threshold,
        iou_threshold=settings.model_iou_threshold,
        class_ids=(settings.model_fod_class_id,),
    )
    pt_adapter = UltralyticsPtModelAdapter(
        source_path=settings.model_source_path,
        device=settings.model_fallback_device,
        image_size=settings.model_image_size,
        confidence_threshold=settings.model_confidence_threshold,
        iou_threshold=settings.model_iou_threshold,
        class_ids=(settings.model_fod_class_id,),
    )

    if runtime == "auto":
        return AutoFallbackModelAdapter(primary=tensorrt_adapter, fallback=pt_adapter)
    if runtime in {"tensorrt", "engine"}:
        return tensorrt_adapter
    if runtime in {"pt", "pytorch", "ultralytics"}:
        return pt_adapter
    if runtime == "cpu":
        return UltralyticsPtModelAdapter(
            source_path=settings.model_source_path,
            device="cpu",
            image_size=settings.model_image_size,
            confidence_threshold=settings.model_confidence_threshold,
            iou_threshold=settings.model_iou_threshold,
            class_ids=(settings.model_fod_class_id,),
        )
    raise ModelIntegrationError(f"unsupported model runtime: {settings.model_runtime}")


def create_model_adapters(settings: Settings) -> dict[str, ModelAdapter]:
    """Create the three strict TensorRT adapters used by the live runtime."""
    return {
        camera_id: TensorRTModelAdapter(
            engine_path=engine_path,
            device=settings.model_device,
            image_size=settings.model_image_size,
            confidence_threshold=settings.model_confidence_threshold,
            iou_threshold=settings.model_iou_threshold,
            class_ids=(settings.model_fod_class_id,),
        )
        for camera_id, engine_path in settings.model_engine_paths.items()
    }
