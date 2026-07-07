import pytest

from app.detection.temporal_validator import (
    TemporalValidationConfig,
    TemporalValidator,
    calculate_iou,
)
from app.core.config import Settings
from app.detection.config import create_temporal_validation_config
from app.detection.types import BoundingBox, Detection


def make_detection(
    class_id: int = 1,
    class_name: str = "Bolt",
    x1: int = 10,
    y1: int = 10,
    x2: int = 30,
    y2: int = 30,
) -> Detection:
    return Detection(
        class_id=class_id,
        class_name=class_name,
        confidence=0.9,
        bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
    )


def test_calculate_iou_for_overlapping_boxes() -> None:
    first = BoundingBox(0, 0, 10, 10)
    second = BoundingBox(5, 5, 15, 15)

    assert calculate_iou(first, second) == pytest.approx(25 / 175)


def test_persistent_detection_confirms_after_required_hits() -> None:
    validator = TemporalValidator(
        TemporalValidationConfig(window_size=5, required_hits=3, match_iou=0.3)
    )
    detection = make_detection()

    assert validator.process([detection], sequence_id=1) == []
    assert validator.process([detection], sequence_id=2) == []
    confirmed = validator.process([detection], sequence_id=3)

    assert confirmed == [detection]
    assert validator.process([detection], sequence_id=4) == []


def test_intermittent_detection_confirms_within_window() -> None:
    validator = TemporalValidator(
        TemporalValidationConfig(window_size=5, required_hits=3, match_iou=0.3)
    )
    detection = make_detection()

    validator.process([detection], sequence_id=1)
    validator.process([], sequence_id=2)
    validator.process([detection], sequence_id=3)
    confirmed = validator.process([detection], sequence_id=5)

    assert confirmed == [detection]


def test_isolated_false_positive_does_not_confirm() -> None:
    validator = TemporalValidator(
        TemporalValidationConfig(window_size=5, required_hits=2, match_iou=0.3)
    )

    assert validator.process([make_detection()], sequence_id=1) == []
    assert validator.process([], sequence_id=2) == []


def test_spatially_separate_same_class_objects_do_not_merge() -> None:
    validator = TemporalValidator(
        TemporalValidationConfig(window_size=5, required_hits=2, match_iou=0.3)
    )
    first = make_detection(x1=0, y1=0, x2=20, y2=20)
    second = make_detection(x1=80, y1=80, x2=100, y2=100)

    validator.process([first], sequence_id=1)
    validator.process([second], sequence_id=2)

    assert len(validator.candidates) == 2
    assert validator.process([second], sequence_id=3) == [second]


def test_old_candidate_state_expires_from_window() -> None:
    validator = TemporalValidator(
        TemporalValidationConfig(window_size=3, required_hits=2, match_iou=0.3)
    )
    detection = make_detection()

    validator.process([detection], sequence_id=1)
    validator.process([], sequence_id=4)

    assert validator.candidates == ()
    assert validator.process([detection], sequence_id=5) == []


def test_disabled_temporal_validation_bypasses_confirmation_rules() -> None:
    validator = TemporalValidator(
        TemporalValidationConfig(enabled=False, window_size=5, required_hits=3)
    )
    detection = make_detection()

    assert validator.process([detection], sequence_id=1) == [detection]


def test_temporal_config_rejects_required_hits_larger_than_window() -> None:
    with pytest.raises(ValueError, match="required_hits"):
        TemporalValidationConfig(window_size=2, required_hits=3)


def test_temporal_config_factory_uses_settings_values() -> None:
    settings = Settings(
        temporal_validation_enabled=False,
        temporal_window_size=7,
        temporal_required_hits=4,
        temporal_match_iou=0.45,
    )

    config = create_temporal_validation_config(settings)

    assert config.enabled is False
    assert config.window_size == 7
    assert config.required_hits == 4
    assert config.match_iou == 0.45
