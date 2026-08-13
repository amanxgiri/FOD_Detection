from pathlib import Path

from app.core.config import Settings


def test_settings_defaults_match_prototype_contract() -> None:
    settings = Settings()

    assert settings.model_source_path == Path("backend/models/weights/model_weight.pt")
    assert settings.model_engine_path == Path("backend/models/weights/model_weight.engine")
    assert settings.model_runtime == "tensorrt"
    assert settings.model_device == "cuda:0"
    assert settings.model_fallback_device == "cpu"
    assert settings.model_confidence_threshold == 0.01
    assert settings.model_fod_class_id == 0
    assert settings.camera_sources == {
        "camera_1": "0",
        "camera_2": "1",
        "camera_3": "2",
    }
    assert settings.model_engine_paths == {
        "camera_1": Path("backend/models/weights/model_1.engine"),
        "camera_2": Path("backend/models/weights/model_2.engine"),
        "camera_3": Path("backend/models/weights/model_3.engine"),
    }
    assert settings.model_source_paths == {
        "camera_1": Path("backend/models/weights/model_1.pt"),
        "camera_2": Path("backend/models/weights/model_2.pt"),
        "camera_3": Path("backend/models/weights/model_3.pt"),
    }
    assert settings.frontend_origin == "http://localhost:5173"
