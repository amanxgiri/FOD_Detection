from pathlib import Path

import pytest

from app.inference.model_adapter import (
    ModelArtifactNotFoundError,
    ModelRuntimeUnavailableError,
)
from app.inference.tensorrt_export import (
    TensorRTExportConfig,
    format_export_config,
    validate_cuda_available,
)


def test_export_config_format_includes_key_paths(tmp_path: Path) -> None:
    config = TensorRTExportConfig(
        source_path=tmp_path / "model_weight.pt",
        engine_path=tmp_path / "model_weight.engine",
    )

    rendered = format_export_config(config)

    assert "model_weight.pt" in rendered
    assert "model_weight.engine" in rendered
    assert "cuda:0" in rendered


def test_cuda_validation_rejects_cpu_device() -> None:
    with pytest.raises(ModelRuntimeUnavailableError, match="CUDA"):
        validate_cuda_available("cpu")


def test_export_rejects_missing_source_before_runtime_checks(tmp_path: Path) -> None:
    from app.inference.tensorrt_export import export_tensorrt_engine

    config = TensorRTExportConfig(
        source_path=tmp_path / "missing.pt",
        engine_path=tmp_path / "model_weight.engine",
    )

    with pytest.raises(ModelArtifactNotFoundError):
        export_tensorrt_engine(config)
