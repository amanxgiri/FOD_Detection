from app.api.websocket.events import (
    BoundingBoxEventData,
    FodAcknowledgedData,
    FodDetectedData,
    make_event,
)
from datetime import UTC, datetime
from app.detection.types import BoundingBox


def test_fod_detected_event_schema_is_serializable() -> None:
    event = make_event(
        "fod.detected",
        FodDetectedData(
            detection_id="DET-20260707-000001",
            class_name="Bolt",
            confidence=0.91,
            bbox=BoundingBoxEventData.from_bbox(BoundingBox(1, 2, 10, 20)),
            evidence_url="/api/v1/detections/DET-20260707-000001/evidence",
        ),
    )

    payload = event.model_dump(mode="json")

    assert payload["type"] == "fod.detected"
    assert payload["data"]["detection_id"] == "DET-20260707-000001"
    assert payload["data"]["bbox"] == {"x1": 1, "y1": 2, "x2": 10, "y2": 20}
    assert isinstance(payload["timestamp"], str)


def test_fod_acknowledged_event_schema_is_serializable() -> None:
    acknowledged_at = datetime(2026, 7, 7, 9, 5, tzinfo=UTC)

    event = make_event(
        "fod.acknowledged",
        FodAcknowledgedData(
            detection_id="DET-20260707-000001",
            status="ACKNOWLEDGED",
            acknowledged_at=acknowledged_at,
        ),
    )

    payload = event.model_dump(mode="json")

    assert payload["type"] == "fod.acknowledged"
    assert payload["data"]["detection_id"] == "DET-20260707-000001"
    assert payload["data"]["status"] == "ACKNOWLEDGED"
    assert payload["data"]["acknowledged_at"] == "2026-07-07T09:05:00Z"
