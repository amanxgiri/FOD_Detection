import builtins
from pathlib import Path

import numpy as np
import pytest

from app.inference.model_adapter import (
    ModelArtifactNotFoundError,
    ModelNotLoadedError,
    ModelRuntimeUnavailableError,
    TensorRTModelAdapter,
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
