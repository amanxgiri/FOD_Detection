from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.api.websocket.events import FodAcknowledgedData, make_event
from app.api.websocket.connection_manager import WebSocketConnectionManager
from app.schemas.detection import (
    BoundingBoxResponse,
    DetectionDetailResponse,
    DetectionListResponse,
    DetectionSummaryResponse,
)
from app.storage.evidence_store import EvidenceStore
from app.storage.models import DetectionRecord
from app.storage.repositories.detection_repository import DetectionRepository

router = APIRouter(prefix="/detections")


def get_db_session(request: Request) -> Iterator[Session]:
    session_factory: sessionmaker[Session] | None = getattr(
        request.app.state,
        "session_factory",
        None,
    )
    if session_factory is None:
        raise HTTPException(status_code=503, detail="database is not initialized")
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@router.get("", response_model=DetectionListResponse)
def list_detections(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: str | None = None,
    session: Session = Depends(get_db_session),
) -> DetectionListResponse:
    repository = DetectionRepository(session)
    try:
        records = repository.list_detections(limit=limit, offset=offset, status=status)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="database query failed") from exc
    return DetectionListResponse(
        items=[to_summary(record, request) for record in records],
        limit=limit,
        offset=offset,
    )


@router.get("/{detection_id}", response_model=DetectionDetailResponse)
def get_detection(
    detection_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
) -> DetectionDetailResponse:
    record = get_record_or_404(detection_id, session)
    return to_detail(record, request)


@router.get("/{detection_id}/evidence")
def get_detection_evidence(
    detection_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
) -> FileResponse:
    record = get_record_or_404(detection_id, session)
    evidence_store = get_evidence_store(request)
    path = evidence_store.resolve(record.evidence_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="evidence image not found")
    return FileResponse(path, media_type="image/jpeg")


@router.post("/{detection_id}/acknowledge", response_model=DetectionDetailResponse)
async def acknowledge_detection(
    detection_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
) -> DetectionDetailResponse:
    repository = DetectionRepository(session)
    try:
        record = repository.acknowledge_detection(detection_id)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="database update failed") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="detection not found")

    if record.acknowledged_at is not None:
        manager = get_websocket_manager(request)
        await manager.broadcast(
            make_event(
                "fod.acknowledged",
                FodAcknowledgedData(
                    detection_id=record.id,
                    status=record.status,
                    acknowledged_at=record.acknowledged_at,
                ),
            )
        )
    return to_detail(record, request)


def get_evidence_store(request: Request) -> EvidenceStore:
    store: EvidenceStore | None = getattr(request.app.state, "evidence_store", None)
    if store is None:
        raise HTTPException(status_code=503, detail="evidence store is not initialized")
    return store


def get_websocket_manager(request: Request) -> WebSocketConnectionManager:
    manager: WebSocketConnectionManager | None = getattr(
        request.app.state,
        "websocket_manager",
        None,
    )
    if manager is None:
        manager = WebSocketConnectionManager()
        request.app.state.websocket_manager = manager
    return manager


def get_record_or_404(detection_id: str, session: Session) -> DetectionRecord:
    repository = DetectionRepository(session)
    try:
        record = repository.get_detection(detection_id)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="database query failed") from exc
    if record is None:
        raise HTTPException(status_code=404, detail="detection not found")
    return record


def to_summary(record: DetectionRecord, request: Request) -> DetectionSummaryResponse:
    return DetectionSummaryResponse(
        id=record.id,
        timestamp=record.event_timestamp,
        class_name=record.class_name,
        confidence=record.confidence,
        status=record.status,
        evidence_url=str(request.url_for("get_detection_evidence", detection_id=record.id)),
    )


def to_detail(record: DetectionRecord, request: Request) -> DetectionDetailResponse:
    summary = to_summary(record, request)
    return DetectionDetailResponse(
        **summary.model_dump(),
        class_id=record.class_id,
        bbox=BoundingBoxResponse(
            x1=record.bbox_x1,
            y1=record.bbox_y1,
            x2=record.bbox_x2,
            y2=record.bbox_y2,
        ),
        acknowledged_at=record.acknowledged_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
