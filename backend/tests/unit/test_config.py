from pathlib import Path

from app.core.config import Settings


def test_settings_defaults_match_prototype_contract() -> None:
    settings = Settings()

    assert settings.model_source_path == Path("backend/models/weights/model_weight.pt")
    assert settings.model_engine_path == Path("backend/models/weights/model_weight.engine")
    assert settings.model_runtime == "auto"
    assert settings.model_device == "cuda:0"
    assert settings.model_fallback_device == "cpu"
    assert settings.model_confidence_threshold == 0.01
    assert settings.frontend_origin == "http://localhost:5173"
