from datetime import datetime

from pydantic import BaseModel


class BoundingBoxResponse(BaseModel):
    x1: int
    y1: int
    x2: int
    y2: int


class DetectionSummaryResponse(BaseModel):
    id: str
    timestamp: datetime
    class_name: str
    confidence: float
    status: str
    evidence_url: str


class DetectionDetailResponse(DetectionSummaryResponse):
    class_id: int
    bbox: BoundingBoxResponse
    acknowledged_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DetectionListResponse(BaseModel):
    items: list[DetectionSummaryResponse]
    limit: int
    offset: int
