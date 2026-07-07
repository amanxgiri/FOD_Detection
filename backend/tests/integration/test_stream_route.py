from datetime import UTC, datetime

import numpy as np
from fastapi.testclient import TestClient

from app.inference.annotated_frame_store import AnnotatedFrame
from app.main import create_app


def test_stream_endpoint_returns_mjpeg_frame_from_store() -> None:
    app = create_app()
    app.state.annotated_frame_store.publish(
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


def test_stream_endpoint_returns_placeholder_without_running_inference() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/stream?frame_limit=1")

    assert response.status_code == 200
    assert b"Content-Type: image/jpeg" in response.content
