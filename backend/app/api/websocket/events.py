from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.detection.types import BoundingBox

EventType = Literal[
    "fod.detected",
    "fod.acknowledged",
    "camera.offline",
    "camera.online",
    "system.warning",
]


class EventEnvelope(BaseModel):
    type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data: dict[str, Any]


class BoundingBoxEventData(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int

    @classmethod
    def from_bbox(cls, bbox: BoundingBox) -> "BoundingBoxEventData":
        return cls(x1=bbox.x1, y1=bbox.y1, x2=bbox.x2, y2=bbox.y2)


class FodDetectedData(BaseModel):
    detection_id: str
    class_name: str
    confidence: float
    bbox: BoundingBoxEventData
    evidence_url: str


class FodAcknowledgedData(BaseModel):
    detection_id: str
    status: str
    acknowledged_at: datetime


class SystemWarningData(BaseModel):
    message: str


def make_event(event_type: EventType, data: BaseModel | dict[str, Any]) -> EventEnvelope:
    payload = data.model_dump() if isinstance(data, BaseModel) else data
    return EventEnvelope(type=event_type, data=payload)
