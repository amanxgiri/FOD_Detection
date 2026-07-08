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
