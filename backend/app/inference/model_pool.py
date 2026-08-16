from __future__ import annotations

import threading

from app.core.config import Settings
from app.inference.model_adapter import ModelAdapter, TensorRTModelAdapter
from app.inference.model_catalog import ModelCatalog


class ModelPool:
    """Load each TensorRT engine once and share it across serialized lanes."""

    def __init__(self, settings: Settings, catalog: ModelCatalog) -> None:
        self._settings = settings
        self._catalog = catalog
        self._lock = threading.RLock()
        self._adapters: dict[str, ModelAdapter] = {}
        self._references: dict[str, int] = {}

    def acquire(self, model_id: str) -> ModelAdapter:
        with self._lock:
            current = self._adapters.get(model_id)
            if current is not None:
                self._references[model_id] = self._references.get(model_id, 0) + 1
                return current
            entry = self._catalog.get(model_id)
            if entry is None:
                raise ValueError(f"unknown or unavailable model: {model_id}")
            adapter = TensorRTModelAdapter(
                engine_path=entry.engine_path,
                device=self._settings.model_device,
                image_size=self._settings.model_image_size,
                confidence_threshold=self._settings.model_confidence_threshold,
                iou_threshold=self._settings.model_iou_threshold,
                class_ids=(self._settings.model_fod_class_id,),
            )
            adapter.load()
            adapter.warmup()
            self._adapters[model_id] = adapter
            self._references[model_id] = 1
            return adapter

    def release(self, model_id: str) -> None:
        """Release a lane reference; adapters remain warm until the runtime stops."""
        with self._lock:
            count = self._references.get(model_id, 0)
            if count <= 1:
                self._references.pop(model_id, None)
            else:
                self._references[model_id] = count - 1

    def reference_count(self, model_id: str) -> int:
        with self._lock:
            return self._references.get(model_id, 0)

    def close_all(self) -> None:
        with self._lock:
            adapters = list(self._adapters.values())
            self._adapters.clear()
            self._references.clear()
        for adapter in adapters:
            adapter.close()
