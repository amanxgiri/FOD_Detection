from dataclasses import dataclass
from datetime import datetime

from app.detection.types import Detection


@dataclass(frozen=True)
class AlertRecord:
    detection_id: str
    timestamp: datetime
    detection: Detection
    evidence_url: str
