from datetime import UTC, datetime

import numpy as np
from fastapi.testclient import TestClient

from app.detection.types import BoundingBox, Detection
from app.main import create_app
from app.storage.repositories.detection_repository import DetectionRepository
from tests.storage_helpers import configure_test_storage


def test_detection_history_detail_and_evidence_endpoints(tmp_path) -> None:
    app = create_app()
    configure_test_storage(app, tmp_path)
    session = app.state.session_factory()
    timestamp = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)
    detection = Detection(1, "Bolt", 0.91, BoundingBox(1, 2, 20, 30))
    frame = np.full((20, 30, 3), 120, dtype=np.uint8)
    evidence_path = app.state.evidence_store.save(
        "DET-20260707-000001",
        frame,
        timestamp,
    )
    DetectionRepository(session).create_detection(
        detection_id="DET-20260707-000001",
        event_timestamp=timestamp,
        detection=detection,
        evidence_path=evidence_path,
    )
    session.close()
    client = TestClient(app)

    history = client.get("/api/v1/detections")
    detail = client.get("/api/v1/detections/DET-20260707-000001")
    evidence = client.get("/api/v1/detections/DET-20260707-000001/evidence")

    assert history.status_code == 200
    assert history.json()["items"][0]["id"] == "DET-20260707-000001"
    assert detail.status_code == 200
    assert detail.json()["bbox"] == {"x1": 1, "y1": 2, "x2": 20, "y2": 30}
    assert evidence.status_code == 200
    assert evidence.headers["content-type"] == "image/jpeg"
    assert evidence.content.startswith(b"\xff\xd8")


def test_detection_detail_returns_404_for_missing_record(tmp_path) -> None:
    app = create_app()
    configure_test_storage(app, tmp_path)
    client = TestClient(app)

    response = client.get("/api/v1/detections/DET-missing")

    assert response.status_code == 404


def test_detection_history_reports_database_initialization_failure() -> None:
    app = create_app()
    app.state.session_factory = None
    client = TestClient(app)

    response = client.get("/api/v1/detections")

    assert response.status_code == 503
