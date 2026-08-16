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
        self.added: list[tuple[str, str]] = []

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

    def add_camera(self, camera_id: str, rtsp_path: str, selected_model_id=None,
                   source_override=None) -> bool:
        del selected_model_id
        self.added.append((camera_id, source_override or rtsp_path))
        return True


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


def test_manually_adds_rtsp_camera_and_rejects_duplicate(tmp_path) -> None:
    app = create_camera_app(tmp_path)
    client = TestClient(app)
    url = "rtsp://viewer:secret@192.168.1.220:8554/runway"

    added = client.post("/api/v1/cameras", json={"rtsp_url": url})
    duplicate = client.post("/api/v1/cameras", json={"rtsp_url": url})
    invalid = client.post("/api/v1/cameras", json={"rtsp_url": "http://camera/video"})

    assert added.status_code == 201
    assert added.json()["display_name"] == "runway"
    assert added.json()["rtsp_path"] == "rtsp://192.168.1.220:8554/runway"
    assert "secret" not in added.text
    assert app.state.runtime_controller.added[0][1] == url
    assert duplicate.status_code == 409
    assert invalid.status_code == 422


def test_manually_adds_local_camera_index_and_device_path(tmp_path) -> None:
    app = create_camera_app(tmp_path)
    client = TestClient(app)

    index_camera = client.post("/api/v1/cameras", json={"source": "0"})
    device_camera = client.post("/api/v1/cameras", json={"source": "/dev/video2"})

    assert index_camera.status_code == 201
    assert index_camera.json()["display_name"] == "Local camera 0"
    assert index_camera.json()["rtsp_path"] == "0"
    assert index_camera.json()["publisher_ip"] is None
    assert device_camera.status_code == 201
    assert device_camera.json()["display_name"] == "video2"
    assert app.state.runtime_controller.added[-2][1] == "0"
    assert app.state.runtime_controller.added[-1][1] == "/dev/video2"


def test_manual_camera_source_validation_and_legacy_rtsp_field(tmp_path) -> None:
    app = create_camera_app(tmp_path)
    client = TestClient(app)

    legacy = client.post(
        "/api/v1/cameras", json={"rtsp_url": "rtsp://192.168.1.221/live"}
    )
    invalid_path = client.post("/api/v1/cameras", json={"source": "/tmp/video.mp4"})
    invalid_index = client.post("/api/v1/cameras", json={"source": "999"})

    assert legacy.status_code == 201
    assert invalid_path.status_code == 422
    assert invalid_index.status_code == 422
