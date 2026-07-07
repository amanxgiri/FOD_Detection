from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.inference.model_adapter import (
    ModelArtifactNotFoundError,
    ModelIntegrationError,
    ModelRuntimeUnavailableError,
)
from app.inference.model_loader import validate_source_model


@dataclass(frozen=True)
class TensorRTExportConfig:
    source_path: Path
    engine_path: Path
    device: str = "cuda:0"
    image_size: int = 640
    half: bool = True
    workspace: int | None = None


def validate_cuda_available(device: str) -> None:
    if not device.startswith("cuda"):
        raise ModelRuntimeUnavailableError(
            f"TensorRT export requires a CUDA device, got {device!r}"
        )
    try:
        import torch
    except ImportError as exc:
        raise ModelRuntimeUnavailableError(
            "PyTorch with CUDA support is required to validate TensorRT export prerequisites"
        ) from exc

    if not torch.cuda.is_available():
        raise ModelRuntimeUnavailableError(
            "CUDA is not available; TensorRT export will not fall back to CPU"
        )

    if ":" in device:
        device_index = int(device.split(":", maxsplit=1)[1])
        if device_index >= torch.cuda.device_count():
            raise ModelRuntimeUnavailableError(
                f"configured CUDA device {device!r} is outside available device count"
            )


def export_tensorrt_engine(config: TensorRTExportConfig) -> Path:
    validate_source_model(config.source_path)
    validate_cuda_available(config.device)

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise ModelRuntimeUnavailableError(
            "Ultralytics is required to export the supplied .pt model to TensorRT"
        ) from exc

    model = YOLO(str(config.source_path))
    export_kwargs: dict[str, Any] = {
        "format": "engine",
        "imgsz": config.image_size,
        "device": config.device,
        "half": config.half,
    }
    if config.workspace is not None:
        export_kwargs["workspace"] = config.workspace

    exported_path = Path(model.export(**export_kwargs))
    if not exported_path.exists():
        raise ModelArtifactNotFoundError(
            f"Ultralytics reported export path that does not exist: {exported_path}"
        )

    config.engine_path.parent.mkdir(parents=True, exist_ok=True)
    if exported_path.resolve() != config.engine_path.resolve():
        shutil.copy2(exported_path, config.engine_path)

    if not config.engine_path.exists():
        raise ModelArtifactNotFoundError(
            f"TensorRT export did not create engine: {config.engine_path}"
        )
    return config.engine_path


def format_export_config(config: TensorRTExportConfig) -> str:
    return (
        "TensorRT export configuration:\n"
        f"  source_path={config.source_path}\n"
        f"  engine_path={config.engine_path}\n"
        f"  device={config.device}\n"
        f"  image_size={config.image_size}\n"
        f"  half={config.half}\n"
        f"  workspace={config.workspace}"
    )
