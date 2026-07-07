import pytest

from app.inference.types import RawDetection


def test_raw_detection_accepts_valid_coordinates() -> None:
    detection = RawDetection(
        class_id=1,
        class_name="Bolt",
        confidence=0.91,
        x1=10.0,
        y1=12.0,
        x2=30.0,
        y2=40.0,
    )

    assert detection.class_name == "Bolt"
    assert detection.confidence == 0.91


def test_raw_detection_rejects_invalid_confidence() -> None:
    with pytest.raises(ValueError, match="confidence"):
        RawDetection(
            class_id=1,
            class_name="Bolt",
            confidence=1.2,
            x1=0.0,
            y1=0.0,
            x2=1.0,
            y2=1.0,
        )


def test_raw_detection_rejects_inverted_box() -> None:
    with pytest.raises(ValueError, match="coordinates"):
        RawDetection(
            class_id=1,
            class_name="Bolt",
            confidence=0.5,
            x1=5.0,
            y1=0.0,
            x2=1.0,
            y2=1.0,
        )
