from app.api.websocket.events import (
    BoundingBoxEventData,
    FodDetectedData,
    make_event,
)
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
