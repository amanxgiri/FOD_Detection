from datetime import UTC, datetime

import numpy as np
import pytest

from app.alerts.alert_manager import AlertManager
from app.api.websocket.connection_manager import WebSocketConnectionManager
from app.detection.types import BoundingBox, Detection
from app.storage import EvidenceStore, create_database_engine, create_session_factory, init_database
from app.storage.repositories.detection_repository import DetectionRepository


class RecordingWebSocketManager(WebSocketConnectionManager):
    def __init__(self) -> None:
        super().__init__()
        self.events = []

    async def broadcast(self, event):
        self.events.append(event)


@pytest.mark.anyio
async def test_alert_manager_persists_detection_and_broadcasts_event(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'fod-test.db'}")
    init_database(engine)
    session = create_session_factory(engine)()
    repository = DetectionRepository(session)
    evidence_store = EvidenceStore(tmp_path / "evidence")
    websocket_manager = RecordingWebSocketManager()
    manager = AlertManager(repository, evidence_store, websocket_manager)
    detection = Detection(1, "Bolt", 0.91, BoundingBox(1, 2, 20, 30))
    timestamp = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)
    frame = np.full((20, 30, 3), 100, dtype=np.uint8)

    alert = await manager.create_fod_alert(
        "DET-20260707-000001",
        detection,
        frame,
        timestamp,
    )

    record = repository.get_detection("DET-20260707-000001")
    assert record is not None
    assert record.class_name == "Bolt"
    assert evidence_store.resolve(record.evidence_path).exists()
    assert alert.evidence_url == "/api/v1/detections/DET-20260707-000001/evidence"
    assert len(websocket_manager.events) == 1
    assert websocket_manager.events[0].type == "fod.detected"
    session.close()


@pytest.mark.anyio
async def test_alert_manager_prevents_duplicate_alert_creation(tmp_path) -> None:
    engine = create_database_engine(f"sqlite:///{tmp_path / 'fod-test.db'}")
    init_database(engine)
    session = create_session_factory(engine)()
    repository = DetectionRepository(session)
    evidence_store = EvidenceStore(tmp_path / "evidence")
    websocket_manager = RecordingWebSocketManager()
    manager = AlertManager(repository, evidence_store, websocket_manager)
    detection = Detection(1, "Bolt", 0.91, BoundingBox(1, 2, 20, 30))
    frame = np.full((20, 30, 3), 100, dtype=np.uint8)
    timestamp = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)

    await manager.create_fod_alert("DET-20260707-000001", detection, frame, timestamp)
    await manager.create_fod_alert("DET-20260707-000001", detection, frame, timestamp)

    assert len(repository.list_detections(limit=10, offset=0)) == 1
    assert len(websocket_manager.events) == 1
    session.close()
