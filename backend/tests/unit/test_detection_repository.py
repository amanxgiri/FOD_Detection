from datetime import UTC, datetime

from app.detection.types import BoundingBox, Detection
from app.storage import create_database_engine, create_session_factory, init_database
from app.storage.repositories.detection_repository import DetectionRepository


def test_detection_repository_creates_lists_and_reads_detection(tmp_path) -> None:
    session_factory = create_test_session_factory(tmp_path)
    session = session_factory()
    repository = DetectionRepository(session)
    detection = Detection(1, "Bolt", 0.91, BoundingBox(1, 2, 20, 30))
    timestamp = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)

    created = repository.create_detection(
        detection_id="DET-20260707-000001",
        event_timestamp=timestamp,
        detection=detection,
        evidence_path="2026/07/07/DET-20260707-000001.jpg",
    )

    assert created.id == "DET-20260707-000001"
    assert repository.get_detection(created.id) is not None
    assert repository.list_detections(limit=20, offset=0)[0].class_name == "Bolt"
    session.close()


def test_detection_repository_acknowledges_detection(tmp_path) -> None:
    session_factory = create_test_session_factory(tmp_path)
    session = session_factory()
    repository = DetectionRepository(session)
    detection = Detection(1, "Bolt", 0.91, BoundingBox(1, 2, 20, 30))
    repository.create_detection(
        detection_id="DET-20260707-000001",
        event_timestamp=datetime(2026, 7, 7, 9, 0, tzinfo=UTC),
        detection=detection,
        evidence_path="2026/07/07/DET-20260707-000001.jpg",
    )

    acknowledged = repository.acknowledge_detection("DET-20260707-000001")

    assert acknowledged is not None
    assert acknowledged.status == "ACKNOWLEDGED"
    assert acknowledged.acknowledged_at is not None
    session.close()


def test_detection_repository_repeat_acknowledgement_preserves_timestamp(tmp_path) -> None:
    session_factory = create_test_session_factory(tmp_path)
    session = session_factory()
    repository = DetectionRepository(session)
    detection = Detection(1, "Bolt", 0.91, BoundingBox(1, 2, 20, 30))
    repository.create_detection(
        detection_id="DET-20260707-000001",
        event_timestamp=datetime(2026, 7, 7, 9, 0, tzinfo=UTC),
        detection=detection,
        evidence_path="2026/07/07/DET-20260707-000001.jpg",
    )
    first = repository.acknowledge_detection("DET-20260707-000001")
    second = repository.acknowledge_detection("DET-20260707-000001")

    assert first is not None
    assert second is not None
    assert second.acknowledged_at == first.acknowledged_at
    session.close()


def create_test_session_factory(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'fod-test.db'}")
    init_database(engine)
    return create_session_factory(engine)
