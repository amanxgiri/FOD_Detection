from app.core.config import Settings
from app.detection.temporal_validator import TemporalValidationConfig


def create_temporal_validation_config(settings: Settings) -> TemporalValidationConfig:
    return TemporalValidationConfig(
        enabled=settings.temporal_validation_enabled,
        window_size=settings.temporal_window_size,
        required_hits=settings.temporal_required_hits,
        match_iou=settings.temporal_match_iou,
    )
