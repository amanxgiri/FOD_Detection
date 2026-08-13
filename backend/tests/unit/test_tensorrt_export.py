from pathlib import Path

import pytest

from app.inference.model_adapter import (
    ModelArtifactNotFoundError,
    ModelIntegrationError,
    ModelRuntimeUnavailableError,
)
from app.inference.tensorrt_export import (
    TensorRTExportConfig,
    ensure_tensorrt_engines,
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


def test_ensure_tensorrt_engines_exports_only_missing_engine_with_source(
    tmp_path: Path,
) -> None:
    source_1 = tmp_path / "model_1.pt"
    source_2 = tmp_path / "model_2.pt"
    source_1.write_bytes(b"source")
    source_2.write_bytes(b"source")
    engine_2 = tmp_path / "model_2.engine"
    engine_2.write_bytes(b"existing")
    exported_configs: list[TensorRTExportConfig] = []

    def fake_exporter(config: TensorRTExportConfig) -> Path:
        exported_configs.append(config)
        config.engine_path.write_bytes(b"generated")
        return config.engine_path

    generated = ensure_tensorrt_engines(
        source_paths={
            "camera_1": source_1,
            "camera_2": source_2,
            "camera_3": tmp_path / "missing.pt",
        },
        engine_paths={
            "camera_1": tmp_path / "model_1.engine",
            "camera_2": engine_2,
            "camera_3": tmp_path / "model_3.engine",
        },
        device="cuda:0",
        image_size=640,
        exporter=fake_exporter,
    )

    assert [path.name for path in generated] == ["model_1.engine"]
    assert len(exported_configs) == 1
    assert exported_configs[0].source_path == source_1
    assert engine_2.read_bytes() == b"existing"


def test_ensure_tensorrt_engines_identifies_failed_camera(tmp_path: Path) -> None:
    source = tmp_path / "model_1.pt"
    source.write_bytes(b"source")

    def failing_exporter(config: TensorRTExportConfig) -> Path:
        raise ModelRuntimeUnavailableError("CUDA unavailable")

    with pytest.raises(ModelIntegrationError, match="camera_1.*CUDA unavailable"):
        ensure_tensorrt_engines(
            source_paths={"camera_1": source},
            engine_paths={"camera_1": tmp_path / "model_1.engine"},
            device="cuda:0",
            image_size=640,
            exporter=failing_exporter,
        )
