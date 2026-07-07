from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.detection.types import Detection
from app.storage.models import DetectionRecord


class DetectionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_detection(
        self,
        detection_id: str,
        event_timestamp: datetime,
        detection: Detection,
        evidence_path: str,
    ) -> DetectionRecord:
        record = DetectionRecord(
            id=detection_id,
            event_timestamp=event_timestamp,
            class_id=detection.class_id,
            class_name=detection.class_name,
            confidence=detection.confidence,
            bbox_x1=detection.bbox.x1,
            bbox_y1=detection.bbox.y1,
            bbox_x2=detection.bbox.x2,
            bbox_y2=detection.bbox.y2,
            evidence_path=evidence_path,
            status="ACTIVE",
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_detection(self, detection_id: str) -> DetectionRecord | None:
        return self.session.get(DetectionRecord, detection_id)

    def list_detections(
        self,
        limit: int,
        offset: int,
        status: str | None = None,
    ) -> list[DetectionRecord]:
        statement = select(DetectionRecord).order_by(DetectionRecord.event_timestamp.desc())
        if status is not None:
            statement = statement.where(DetectionRecord.status == status)
        statement = statement.limit(limit).offset(offset)
        return list(self.session.scalars(statement))

    def acknowledge_detection(
        self,
        detection_id: str,
        acknowledged_at: datetime | None = None,
    ) -> DetectionRecord | None:
        record = self.get_detection(detection_id)
        if record is None:
            return None
        record.status = "ACKNOWLEDGED"
        record.acknowledged_at = acknowledged_at or datetime.now(UTC)
        record.updated_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(record)
        return record
