from __future__ import annotations

from datetime import datetime

from app.alerts.types import AlertRecord
from app.api.websocket.connection_manager import WebSocketConnectionManager
from app.api.websocket.events import (
    BoundingBoxEventData,
    FodDetectedData,
    make_event,
)
from app.camera.types import FrameArray
from app.detection.types import Detection
from app.storage.evidence_store import EvidenceStore
from app.storage.repositories.detection_repository import DetectionRepository


class AlertManager:
    def __init__(
        self,
        repository: DetectionRepository,
        evidence_store: EvidenceStore,
        websocket_manager: WebSocketConnectionManager,
        api_prefix: str = "/api/v1",
    ) -> None:
        self._repository = repository
        self._evidence_store = evidence_store
        self._websocket_manager = websocket_manager
        self._api_prefix = api_prefix.rstrip("/")
        self._created_detection_ids: set[str] = set()

    async def create_fod_alert(
        self,
        detection_id: str,
        detection: Detection,
        frame: FrameArray,
        timestamp: datetime,
    ) -> AlertRecord:
        existing = self._repository.get_detection(detection_id)
        if existing is not None or detection_id in self._created_detection_ids:
            evidence_url = f"{self._api_prefix}/detections/{detection_id}/evidence"
            return AlertRecord(
                detection_id=detection_id,
                timestamp=timestamp,
                detection=detection,
                evidence_url=evidence_url,
            )

        evidence_path = self._evidence_store.save(detection_id, frame, timestamp)
        self._repository.create_detection(
            detection_id=detection_id,
            event_timestamp=timestamp,
            detection=detection,
            evidence_path=evidence_path,
        )
        self._created_detection_ids.add(detection_id)
        evidence_url = f"{self._api_prefix}/detections/{detection_id}/evidence"
        event = make_event(
            "fod.detected",
            FodDetectedData(
                detection_id=detection_id,
                class_name=detection.class_name,
                confidence=detection.confidence,
                bbox=BoundingBoxEventData.from_bbox(detection.bbox),
                evidence_url=evidence_url,
            ),
        )
        await self._websocket_manager.broadcast(event)
        return AlertRecord(
            detection_id=detection_id,
            timestamp=timestamp,
            detection=detection,
            evidence_url=evidence_url,
        )
