from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.core.lifecycle import RuntimeStatuses
from app.inference.model_catalog import ModelCatalog
from app.main import create_app
from app.storage.repositories.camera_repository import CameraRepository
from tests.storage_helpers import configure_test_storage


class FakeRuntimeController:
    def __init__(self) -> None:
        self.model_id: str | None = None
        self.removed: list[str] = []

    def get_statuses(self) -> RuntimeStatuses:
        return RuntimeStatuses(
            camera_status="offline",
            model_status="unassigned",
            inference_status="not_started",
            camera_statuses={"raspberrypi9": "offline"},
            model_statuses={"raspberrypi9": "unassigned"},
        )

    def set_model_assignment(self, camera_id: str, model_id: str | None) -> None:
        assert camera_id == "raspberrypi9"
        self.model_id = model_id

    def remove_camera(self, camera_id: str) -> None:
        self.removed.append(camera_id)


def create_camera_app(tmp_path):
    app = create_app()
    configure_test_storage(app, tmp_path)
    app.state.runtime_controller = FakeRuntimeController()
    model_dir = tmp_path / "weights"
    model_dir.mkdir()
    (model_dir / "model_1.engine").touch()
    (model_dir / "model_1.onnx").touch()
    app.state.model_catalog = ModelCatalog(model_dir)
    with app.state.session_factory() as session:
        CameraRepository(session).upsert_discovered(
            "raspberrypi9",
            "raspberrypi9",
            "192.168.1.204",
            datetime.now(UTC),
        )
    return app


def test_dynamic_camera_list_model_catalog_and_assignment(tmp_path) -> None:
    app = create_camera_app(tmp_path)
    client = TestClient(app)

    cameras = client.get("/api/v1/cameras")
    models = client.get("/api/v1/models")
    renamed = client.patch(
        "/api/v1/cameras/raspberrypi9", json={"display_name": "Runway north"}
    )
    assigned = client.put(
        "/api/v1/cameras/raspberrypi9/model", json={"model_id": "model_1"}
    )

    assert cameras.status_code == 200
    assert cameras.json()["items"][0]["id"] == "raspberrypi9"
    assert models.json()["items"] == [
        {"id": "model_1", "display_name": "Model 1", "status": "ready"}
    ]
    assert renamed.json()["display_name"] == "Runway north"
    assert assigned.status_code == 200
    assert assigned.json()["selected_model_id"] == "model_1"
    assert app.state.runtime_controller.model_id == "model_1"


def test_invalid_model_and_offline_removal(tmp_path) -> None:
    app = create_camera_app(tmp_path)
    client = TestClient(app)

    invalid = client.put(
        "/api/v1/cameras/raspberrypi9/model", json={"model_id": "model_missing"}
    )
    removed = client.delete("/api/v1/cameras/raspberrypi9")
    missing = client.get("/api/v1/cameras")

    assert invalid.status_code == 422
    assert removed.status_code == 204
    assert app.state.runtime_controller.removed == ["raspberrypi9"]
    assert missing.json()["items"] == []
