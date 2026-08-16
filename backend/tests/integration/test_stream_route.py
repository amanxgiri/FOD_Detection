from datetime import UTC, datetime

import numpy as np
from fastapi.testclient import TestClient

from app.inference.annotated_frame_store import AnnotatedFrame, LatestAnnotatedFrameStore
from app.main import create_app


def test_stream_endpoint_returns_mjpeg_frame_from_store() -> None:
    app = create_app()
    store = LatestAnnotatedFrameStore()
    app.state.annotated_frame_stores["raspberrypi9"] = store
    app.state.annotated_frame_store = store
    store.publish(
        AnnotatedFrame(
            sequence_id=1,
            captured_at=datetime.now(UTC),
            frame=np.full((20, 30, 3), 80, dtype=np.uint8),
        )
    )
    client = TestClient(app)

    response = client.get("/api/v1/stream?frame_limit=1")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("multipart/x-mixed-replace")
    assert b"Content-Type: image/jpeg" in response.content
    assert b"\xff\xd8" in response.content


def test_stream_endpoint_returns_not_found_without_registered_camera() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/stream?frame_limit=1")

    assert response.status_code == 404


def test_camera_specific_stream_uses_requested_store() -> None:
    app = create_app()
    app.state.annotated_frame_stores["raspberrypi9"] = LatestAnnotatedFrameStore()
    app.state.annotated_frame_stores["raspberrypi9"].publish(
        AnnotatedFrame(
            sequence_id=7,
            captured_at=datetime.now(UTC),
            frame=np.full((20, 30, 3), 160, dtype=np.uint8),
        )
    )
    client = TestClient(app)

    response = client.get("/api/v1/cameras/raspberrypi9/stream?frame_limit=1")

    assert response.status_code == 200
    assert b"Content-Type: image/jpeg" in response.content


def test_unknown_camera_stream_returns_not_found() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/cameras/camera_9/stream?frame_limit=1")

    assert response.status_code == 404
