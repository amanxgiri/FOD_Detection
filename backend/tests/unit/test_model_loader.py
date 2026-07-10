from pathlib import Path

import pytest

from app.core.config import Settings
from app.inference.model_adapter import (
    AutoFallbackModelAdapter,
    ModelArtifactNotFoundError,
    ModelIntegrationError,
    TensorRTModelAdapter,
    UltralyticsPtModelAdapter,
)
from app.inference.model_loader import (
    create_model_adapter,
    validate_engine_model,
    validate_source_model,
)


def test_validate_source_model_accepts_pt_file(tmp_path: Path) -> None:
    source = tmp_path / "model_weight.pt"
    source.write_bytes(b"weights")

    validate_source_model(source)


def test_validate_source_model_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ModelArtifactNotFoundError):
        validate_source_model(tmp_path / "missing.pt")


def test_validate_source_model_rejects_unexpected_suffix(tmp_path: Path) -> None:
    source = tmp_path / "model_weight.onnx"
    source.write_bytes(b"weights")

    with pytest.raises(ModelIntegrationError, match=".pt"):
        validate_source_model(source)


def test_validate_engine_model_accepts_engine_file(tmp_path: Path) -> None:
    engine = tmp_path / "model_weight.engine"
    engine.write_bytes(b"engine")

    validate_engine_model(engine)


def test_create_model_adapter_uses_auto_runtime_by_default() -> None:
    settings = Settings()

    adapter = create_model_adapter(settings)

    assert isinstance(adapter, AutoFallbackModelAdapter)


def test_create_model_adapter_uses_tensorrt_runtime() -> None:
    settings = Settings(model_runtime="tensorrt")

    adapter = create_model_adapter(settings)

    assert isinstance(adapter, TensorRTModelAdapter)


def test_create_model_adapter_uses_pt_runtime() -> None:
    settings = Settings(model_runtime="pt")

    adapter = create_model_adapter(settings)

    assert isinstance(adapter, UltralyticsPtModelAdapter)


def test_create_model_adapter_uses_cpu_runtime() -> None:
    settings = Settings(model_runtime="cpu")

    adapter = create_model_adapter(settings)

    assert isinstance(adapter, UltralyticsPtModelAdapter)
    assert adapter.device == "cpu"


def test_create_model_adapter_rejects_unknown_runtime() -> None:
    settings = Settings(model_runtime="unknown")

    with pytest.raises(ModelIntegrationError, match="unsupported"):
        create_model_adapter(settings)
