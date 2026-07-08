import time

import numpy as np
from fastapi.testclient import TestClient

from app.camera.types import CameraStatus
from app.main import create_app


class EndlessCapture:
    def __init__(self, frame: np.ndarray) -> None:
        self.frame = frame
        self.released = False

    def isOpened(self) -> bool:
        return True

    def read(self) -> tuple[bool, np.ndarray]:
        time.sleep(0.01)
        return True, self.frame.copy()

    def release(self) -> None:
        self.released = True


def test_lifespan_starts_live_camera_stream_and_stops_cleanly() -> None:
    frame = np.full((24, 32, 3), 120, dtype=np.uint8)
    capture = EndlessCapture(frame)
    app = create_app()
    app.state.capture_factory = lambda source: capture

    with TestClient(app) as client:
        response = client.get("/api/v1/stream?frame_limit=1")

        assert response.status_code == 200
        assert b"Content-Type: image/jpeg" in response.content
        assert app.state.annotated_frame_store.get_latest() is not None
        assert app.state.camera_manager.get_status() == CameraStatus.ONLINE

    assert capture.released is True
    assert app.state.camera_manager.get_status() == CameraStatus.STOPPED
