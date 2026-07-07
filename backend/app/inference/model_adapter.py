from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from app.inference.types import RawDetection


class ModelIntegrationError(RuntimeError):
    """Base error for model loading and inference failures."""


class ModelArtifactNotFoundError(ModelIntegrationError):
    """Raised when the configured source or engine artifact is missing."""


class ModelRuntimeUnavailableError(ModelIntegrationError):
    """Raised when required GPU runtime packages or devices are unavailable."""


class ModelNotLoadedError(ModelIntegrationError):
    """Raised when prediction is requested before the model is loaded."""


class ModelAdapter(Protocol):
    def load(self) -> None:
        ...

    def warmup(self) -> None:
        ...

    def predict(self, frame: NDArray[np.uint8]) -> list[RawDetection]:
        ...

    def close(self) -> None:
        ...


class TensorRTModelAdapter:
    """TensorRT engine adapter with explicit GPU-runtime prerequisite checks."""

    def __init__(self, engine_path: Path, device: str = "cuda:0") -> None:
        self.engine_path = engine_path
        self.device = device
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def load(self) -> None:
        if not self.engine_path.exists():
            raise ModelArtifactNotFoundError(
                f"TensorRT engine not found: {self.engine_path}"
            )
        self._validate_tensorrt_runtime()
        self._loaded = True

    def warmup(self) -> None:
        if not self._loaded:
            raise ModelNotLoadedError("TensorRT adapter must be loaded before warmup")

    def predict(self, frame: NDArray[np.uint8]) -> list[RawDetection]:
        if not self._loaded:
            raise ModelNotLoadedError("TensorRT adapter must be loaded before predict")
        if frame.size == 0:
            return []
        raise ModelRuntimeUnavailableError(
            "TensorRT execution bindings are not initialized in this milestone"
        )

    def close(self) -> None:
        self._loaded = False

    def _validate_tensorrt_runtime(self) -> None:
        try:
            import tensorrt  # noqa: F401
        except ImportError as exc:
            raise ModelRuntimeUnavailableError(
                "TensorRT Python package is required for engine inference"
            ) from exc

        if not self.device.startswith("cuda"):
            raise ModelRuntimeUnavailableError(
                f"TensorRT runtime requires a CUDA device, got {self.device!r}"
            )
