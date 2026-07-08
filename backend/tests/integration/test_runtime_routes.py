import time

import numpy as np
from fastapi.testclient import TestClient

from app.inference.model_adapter import ModelIntegrationError
from app.inference.types import RawDetection
from app.main import create_app


class EndlessCapture:
    def __init__(self) -> None:
        self.released = False

    def isOpened(self) -> bool:
        return True

    def read(self) -> tuple[bool, np.ndarray]:
        time.sleep(0.01)
        return True, np.full((24, 32, 3), 120, dtype=np.uint8)

    def release(self) -> None:
        self.released = True


class RuntimeCaptureFactory:
    def __init__(self) -> None:
        self.captures: list[EndlessCapture] = []

    def __call__(self, source: object) -> EndlessCapture:
        capture = EndlessCapture()
        self.captures.append(capture)
        return capture


class FakeModelAdapter:
    def __init__(self) -> None:
        self.loaded = False
        self.warmed = False
        self.closed = False

    def load(self) -> None:
        self.loaded = True

    def warmup(self) -> None:
        self.warmed = True

    def predict(self, frame: np.ndarray) -> list[RawDetection]:
        return []

    def close(self) -> None:
        self.closed = True


class FailingModelAdapter(FakeModelAdapter):
    def load(self) -> None:
        raise ModelIntegrationError("synthetic model load failure")


def test_camera_runtime_commands_stop_and_restart_capture() -> None:
    app = create_runtime_app()

    with TestClient(app) as client:
        wait_for_status(client, "camera_status", "online")

        stopped = client.post("/api/v1/runtime/camera/stop")

        assert stopped.status_code == 200
        assert stopped.json()["camera_status"] == "stopped"

        started = client.post("/api/v1/runtime/camera/start")

        assert started.status_code == 200
        wait_for_status(client, "camera_status", "online")


def test_inference_runtime_commands_load_and_unload_model() -> None:
    adapter = FakeModelAdapter()
    app = create_runtime_app(adapter)

    with TestClient(app) as client:
        wait_for_status(client, "camera_status", "online")

        started = client.post("/api/v1/runtime/inference/start")

        assert started.status_code == 200
        body = started.json()
        assert body["model_status"] == "loaded"
        assert body["inference_status"] == "running"
        assert adapter.loaded is True
        assert adapter.warmed is True

        stopped = client.post("/api/v1/runtime/inference/stop")

        assert stopped.status_code == 200
        body = stopped.json()
        assert body["model_status"] == "unloaded"
        assert body["inference_status"] == "stopped"
        assert adapter.closed is True


def test_inference_runtime_start_returns_model_load_error() -> None:
    app = create_runtime_app(FailingModelAdapter())

    with TestClient(app) as client:
        wait_for_status(client, "camera_status", "online")

        response = client.post("/api/v1/runtime/inference/start")

        assert response.status_code == 409
        assert response.json()["detail"] == "synthetic model load failure"
        status = client.get("/api/v1/system/status").json()
        assert status["model_status"] == "error"
        assert status["inference_status"] == "error"


def test_inference_runtime_requires_running_camera() -> None:
    app = create_runtime_app(FakeModelAdapter())

    with TestClient(app) as client:
        wait_for_status(client, "camera_status", "online")
        client.post("/api/v1/runtime/camera/stop")

        response = client.post("/api/v1/runtime/inference/start")

        assert response.status_code == 409
        assert response.json()["detail"] == "camera must be running before inference starts"


def create_runtime_app(adapter: FakeModelAdapter | None = None):
    app = create_app()
    app.state.capture_factory = RuntimeCaptureFactory()
    if adapter is not None:
        app.state.model_adapter_factory = lambda settings: adapter
    return app


def wait_for_status(
    client: TestClient,
    key: str,
    expected: str,
    timeout_seconds: float = 1.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        body = client.get("/api/v1/system/status").json()
        if body[key] == expected:
            return
        time.sleep(0.01)
    raise AssertionError(f"{key} did not become {expected!r}")
