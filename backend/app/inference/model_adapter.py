from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Protocol

import numpy as np
from numpy.typing import NDArray

from app.core.paths import resolve_project_path
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

    def __init__(
        self,
        engine_path: Path,
        device: str = "cuda:0",
        image_size: int = 640,
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.50,
        model_factory: Callable[[str], Any] | None = None,
    ) -> None:
        self.engine_path = resolve_project_path(engine_path)
        self.device = device
        self.image_size = image_size
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self._model_factory = model_factory
        self._model: Any | None = None
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
        self._model = self._create_model()
        self._loaded = True

    def warmup(self) -> None:
        if not self._loaded:
            raise ModelNotLoadedError("TensorRT adapter must be loaded before warmup")
        warmup_frame = np.zeros((self.image_size, self.image_size, 3), dtype=np.uint8)
        self.predict(warmup_frame)

    def predict(self, frame: NDArray[np.uint8]) -> list[RawDetection]:
        if not self._loaded:
            raise ModelNotLoadedError("TensorRT adapter must be loaded before predict")
        if frame.size == 0:
            return []
        if self._model is None:
            raise ModelRuntimeUnavailableError("TensorRT model runtime is not initialized")

        results = self._model.predict(
            source=frame,
            device=self.device,
            imgsz=self.image_size,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            verbose=False,
        )
        return self._normalize_results(results)

    def close(self) -> None:
        self._model = None
        self._loaded = False

    def _create_model(self) -> Any:
        if self._model_factory is not None:
            return self._model_factory(str(self.engine_path))

        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ModelRuntimeUnavailableError(
                "Ultralytics is required to run the TensorRT engine"
            ) from exc

        return YOLO(str(self.engine_path))

    def _normalize_results(self, results: Any) -> list[RawDetection]:
        detections: list[RawDetection] = []
        for result in results:
            names = getattr(result, "names", None) or getattr(self._model, "names", {})
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue

            for box in boxes:
                class_id = int(self._scalar_value(getattr(box, "cls", 0)))
                confidence = float(self._scalar_value(getattr(box, "conf", 0.0)))
                xyxy = self._array_values(getattr(box, "xyxy", []))
                if xyxy.size < 4:
                    continue
                detections.append(
                    RawDetection(
                        class_id=class_id,
                        class_name=self._class_name(names, class_id),
                        confidence=confidence,
                        x1=float(xyxy[0]),
                        y1=float(xyxy[1]),
                        x2=float(xyxy[2]),
                        y2=float(xyxy[3]),
                    )
                )
        return detections

    @staticmethod
    def _class_name(names: Any, class_id: int) -> str:
        if isinstance(names, dict):
            return str(names.get(class_id, class_id))
        if isinstance(names, (list, tuple)) and 0 <= class_id < len(names):
            return str(names[class_id])
        return str(class_id)

    @staticmethod
    def _scalar_value(value: Any) -> float:
        values = TensorRTModelAdapter._array_values(value)
        if values.size == 0:
            return 0.0
        return float(values[0])

    @staticmethod
    def _array_values(value: Any) -> NDArray[np.float64]:
        if hasattr(value, "detach"):
            value = value.detach()
        if hasattr(value, "cpu"):
            value = value.cpu()
        if hasattr(value, "numpy"):
            value = value.numpy()
        return np.asarray(value, dtype=float).reshape(-1)

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
