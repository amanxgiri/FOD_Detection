import builtins
from pathlib import Path

import numpy as np
import pytest

from app.inference.model_adapter import (
    AutoFallbackModelAdapter,
    ModelArtifactNotFoundError,
    ModelNotLoadedError,
    ModelRuntimeUnavailableError,
    TensorRTModelAdapter,
    UltralyticsPtModelAdapter,
)


def test_tensorrt_adapter_requires_engine_file(tmp_path: Path) -> None:
    adapter = TensorRTModelAdapter(tmp_path / "missing.engine")

    with pytest.raises(ModelArtifactNotFoundError):
        adapter.load()


def test_tensorrt_adapter_reports_missing_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = tmp_path / "model_weight.engine"
    engine.write_bytes(b"engine")
    adapter = TensorRTModelAdapter(engine)
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tensorrt":
            raise ImportError("synthetic missing TensorRT")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ModelRuntimeUnavailableError, match="TensorRT"):
        adapter.load()


def test_tensorrt_adapter_requires_load_before_predict(tmp_path: Path) -> None:
    adapter = TensorRTModelAdapter(tmp_path / "model_weight.engine")

    with pytest.raises(ModelNotLoadedError):
        adapter.predict(np.zeros((8, 8, 3), dtype=np.uint8))


def test_tensorrt_adapter_normalizes_ultralytics_predictions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = tmp_path / "model_weight.engine"
    engine.write_bytes(b"engine")
    model = FakeYoloModel()
    adapter = TensorRTModelAdapter(
        engine,
        device="cuda:0",
        image_size=32,
        confidence_threshold=0.25,
        iou_threshold=0.5,
        model_factory=lambda path: model,
    )
    monkeypatch.setattr(
        TensorRTModelAdapter,
        "_validate_tensorrt_runtime",
        lambda self: None,
    )

    adapter.load()
    detections = adapter.predict(np.zeros((16, 16, 3), dtype=np.uint8))

    assert len(detections) == 1
    assert detections[0].class_id == 2
    assert detections[0].class_name == "washer"
    assert detections[0].confidence == pytest.approx(0.91)
    assert detections[0].x1 == pytest.approx(1.0)
    assert detections[0].y1 == pytest.approx(2.0)
    assert detections[0].x2 == pytest.approx(9.0)
    assert detections[0].y2 == pytest.approx(10.0)
    assert model.last_kwargs["device"] == "cuda:0"
    assert model.last_kwargs["imgsz"] == 32


def test_pt_adapter_normalizes_ultralytics_predictions(tmp_path: Path) -> None:
    source = tmp_path / "model_weight.pt"
    source.write_bytes(b"weights")
    model = FakeYoloModel()
    adapter = UltralyticsPtModelAdapter(
        source,
        device="cpu",
        image_size=48,
        confidence_threshold=0.10,
        iou_threshold=0.4,
        model_factory=lambda path: model,
    )

    adapter.load()
    detections = adapter.predict(np.zeros((16, 16, 3), dtype=np.uint8))

    assert len(detections) == 1
    assert detections[0].class_name == "washer"
    assert model.last_kwargs["device"] == "cpu"
    assert model.last_kwargs["imgsz"] == 48
    assert model.last_kwargs["conf"] == pytest.approx(0.10)


def test_auto_adapter_falls_back_when_primary_load_fails() -> None:
    primary = FakeAdapter(fail_load=True)
    fallback = FakeAdapter()
    adapter = AutoFallbackModelAdapter(primary=primary, fallback=fallback)

    adapter.load()
    adapter.warmup()

    assert adapter.active_adapter is fallback
    assert adapter.fallback_reason == "primary unavailable"
    assert primary.closed
    assert fallback.loaded
    assert fallback.warmed


def test_auto_adapter_falls_back_when_primary_warmup_fails() -> None:
    primary = FakeAdapter(fail_warmup=True)
    fallback = FakeAdapter()
    adapter = AutoFallbackModelAdapter(primary=primary, fallback=fallback)

    adapter.load()
    adapter.warmup()

    assert adapter.active_adapter is fallback
    assert adapter.fallback_reason == "primary warmup failed"
    assert primary.closed
    assert fallback.loaded
    assert fallback.warmed


class FakeYoloModel:
    names = {2: "washer"}

    def __init__(self) -> None:
        self.last_kwargs = {}

    def predict(self, **kwargs):
        self.last_kwargs = kwargs
        return [FakeResult()]


class FakeResult:
    names = {2: "washer"}
    boxes = [
        type(
            "FakeBox",
            (),
            {
                "cls": np.array([2]),
                "conf": np.array([0.91]),
                "xyxy": np.array([[1.0, 2.0, 9.0, 10.0]]),
            },
        )()
    ]


class FakeAdapter:
    def __init__(
        self,
        fail_load: bool = False,
        fail_warmup: bool = False,
    ) -> None:
        self.fail_load = fail_load
        self.fail_warmup = fail_warmup
        self.loaded = False
        self.warmed = False
        self.closed = False

    def load(self) -> None:
        if self.fail_load:
            raise ModelRuntimeUnavailableError("primary unavailable")
        self.loaded = True

    def warmup(self) -> None:
        if self.fail_warmup:
            raise ModelRuntimeUnavailableError("primary warmup failed")
        self.warmed = True

    def predict(self, frame: np.ndarray) -> list:
        return []

    def close(self) -> None:
        self.closed = True
