from __future__ import annotations

import hashlib
import re
from urllib.parse import unquote, urlsplit, urlunsplit

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError

from app.api.websocket.events import make_event
from app.core.lifecycle import RuntimeCommandError, get_runtime_controller
from app.inference.model_catalog import ModelCatalog
from app.schemas.camera import (
    CameraListResponse,
    CameraCreateRequest,
    CameraModelRequest,
    CameraResponse,
    CameraUpdateRequest,
    ModelListResponse,
    ModelResponse,
)
from app.storage.models import CameraRegistration
from app.storage.repositories.camera_repository import CameraRepository

router = APIRouter()
LATENCY_SETUP_MESSAGE = (
    "Capture timing is unavailable. On the Pi, run setup_pi_clock_sync.sh and "
    "install_pi_timestamp_service.sh, then restart its publisher."
)


def _camera_response(request: Request, record: CameraRegistration) -> CameraResponse:
    statuses = get_runtime_controller(request.app).get_statuses()
    stream_status = statuses.camera_statuses.get(record.id, "offline")
    snapshot = request.app.state.performance_monitor.snapshot()
    latency_status, latency_message = _latency_health(
        stream_status=stream_status,
        frames_captured=snapshot.frames_captured_by_camera.get(record.id, 0),
        timestamp_frames=snapshot.source_timestamp_frames_by_camera.get(record.id, 0),
        capture_to_host_ms=snapshot.latest_capture_to_host_ms_by_camera.get(record.id),
        local_source=_is_local_source(record.rtsp_path),
    )
    return CameraResponse(
        id=record.id,
        display_name=record.display_name or record.id,
        hostname=record.id,
        rtsp_path=_safe_rtsp_display(record.rtsp_path),
        publisher_ip=record.publisher_ip,
        stream_status=stream_status,
        selected_model_id=record.selected_model_id,
        model_status=statuses.model_statuses.get(
            record.id, "assigned" if record.selected_model_id else "unassigned"
        ),
        latency_status=latency_status,
        latency_message=latency_message,
        discovered_at=record.discovered_at,
        last_seen_at=record.last_seen_at,
    )


@router.post("/cameras", response_model=CameraResponse, status_code=status.HTTP_201_CREATED)
async def create_camera(payload: CameraCreateRequest, request: Request) -> CameraResponse:
    source, parsed = _validated_camera_source(payload.source or payload.rtsp_url or "")
    camera_id = f"manual-{hashlib.sha256(source.encode()).hexdigest()[:12]}"
    if parsed is None:
        display_name = (
            f"Local camera {source}"
            if source.isdigit()
            else source.rstrip("/").rsplit("/", 1)[-1]
        )
        publisher_ip = None
    else:
        display_name = unquote(parsed.path.rstrip("/").rsplit("/", 1)[-1]) or parsed.hostname
        publisher_ip = parsed.hostname
    with request.app.state.session_factory() as session:
        repository = CameraRepository(session)
        records = repository.list_all()
        if repository.get_by_rtsp_path(source) is not None:
            raise HTTPException(status_code=409, detail="this camera source is already registered")
        if len(records) >= request.app.state.settings.camera_max_count:
            raise HTTPException(status_code=409, detail="camera capacity has been reached")
        try:
            record = repository.create_manual(
                camera_id=camera_id,
                rtsp_url=source,
                display_name=display_name or camera_id,
                publisher_ip=publisher_ip,
            )
        except IntegrityError as exc:
            session.rollback()
            raise HTTPException(status_code=409, detail="camera is already registered") from exc
    try:
        get_runtime_controller(request.app).add_camera(
            record.id, record.rtsp_path, source_override=record.rtsp_path
        )
    except Exception:
        with request.app.state.session_factory() as session:
            CameraRepository(session).delete(record.id)
        raise
    await request.app.state.websocket_manager.broadcast(
        make_event("camera.discovered", {"camera_id": camera_id, "manual": True})
    )
    return _camera_response(request, record)


@router.get("/cameras", response_model=CameraListResponse)
def list_cameras(request: Request) -> CameraListResponse:
    with request.app.state.session_factory() as session:
        records = CameraRepository(session).list_all()
        items = [_camera_response(request, record) for record in records]
    discovery = getattr(request.app.state, "camera_discovery", None)
    return CameraListResponse(
        items=items,
        max_cameras=request.app.state.settings.camera_max_count,
        discovery_status=getattr(discovery, "status", "not_started"),
        warning=getattr(discovery, "warning", None),
    )


@router.get("/models", response_model=ModelListResponse)
def list_models(request: Request) -> ModelListResponse:
    catalog: ModelCatalog = request.app.state.model_catalog
    return ModelListResponse(
        items=[
            ModelResponse(id=item.id, display_name=item.display_name)
            for item in catalog.list_ready()
        ]
    )


@router.patch("/cameras/{camera_id}", response_model=CameraResponse)
async def rename_camera(
    camera_id: str, payload: CameraUpdateRequest, request: Request
) -> CameraResponse:
    name = payload.display_name.strip() if payload.display_name else None
    with request.app.state.session_factory() as session:
        record = CameraRepository(session).update_display_name(camera_id, name)
        if record is None:
            raise HTTPException(status_code=404, detail="camera not found")
        response = _camera_response(request, record)
    await request.app.state.websocket_manager.broadcast(
        make_event("camera.updated", {"camera_id": camera_id})
    )
    return response


@router.put("/cameras/{camera_id}/model", response_model=CameraResponse)
async def assign_model(
    camera_id: str, payload: CameraModelRequest, request: Request
) -> CameraResponse:
    catalog: ModelCatalog = request.app.state.model_catalog
    if payload.model_id is not None and catalog.get(payload.model_id) is None:
        raise HTTPException(status_code=422, detail="model is not ready or does not exist")
    with request.app.state.session_factory() as session:
        repository = CameraRepository(session)
        if repository.get(camera_id) is None:
            raise HTTPException(status_code=404, detail="camera not found")
    try:
        get_runtime_controller(request.app).set_model_assignment(camera_id, payload.model_id)
    except RuntimeCommandError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    with request.app.state.session_factory() as session:
        record = CameraRepository(session).update_model(camera_id, payload.model_id)
        assert record is not None
        response = _camera_response(request, record)
    await request.app.state.websocket_manager.broadcast(
        make_event(
            "camera.model_updated",
            {"camera_id": camera_id, "model_id": payload.model_id},
        )
    )
    return response


@router.delete("/cameras/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_camera(camera_id: str, request: Request) -> Response:
    with request.app.state.session_factory() as session:
        if CameraRepository(session).get(camera_id) is None:
            raise HTTPException(status_code=404, detail="camera not found")
    try:
        get_runtime_controller(request.app).remove_camera(camera_id)
    except RuntimeCommandError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    discovery = getattr(request.app.state, "camera_discovery", None)
    if discovery is not None and not camera_id.startswith("manual-"):
        discovery.suppress_until_disconnect(camera_id)
    with request.app.state.session_factory() as session:
        CameraRepository(session).delete(camera_id)
    await request.app.state.websocket_manager.broadcast(
        make_event("camera.removed", {"camera_id": camera_id})
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _validated_camera_source(value: str):
    source = value.strip()
    if any(character in source for character in "\r\n\x00"):
        raise HTTPException(status_code=422, detail="invalid camera source")
    if source.isdigit():
        camera_index = int(source)
        if camera_index > 255:
            raise HTTPException(status_code=422, detail="camera index must be between 0 and 255")
        return str(camera_index), None
    if re.fullmatch(r"/dev/video\d+", source):
        return source, None

    parsed = urlsplit(source)
    if parsed.scheme.lower() not in {"rtsp", "rtsps"} or not parsed.hostname:
        raise HTTPException(
            status_code=422,
            detail="source must be a camera index, /dev/videoN, or an rtsp:// or rtsps:// URL",
        )
    if parsed.fragment:
        raise HTTPException(status_code=422, detail="RTSP URL fragments are not supported")
    try:
        parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="RTSP URL has an invalid port") from exc
    return source, parsed


def _is_local_source(value: str) -> bool:
    return value.isdigit() or re.fullmatch(r"/dev/video\d+", value) is not None


def _safe_rtsp_display(value: str) -> str:
    if not value.lower().startswith(("rtsp://", "rtsps://")):
        return value
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = f"{host}:{parsed.port}" if parsed.port else host
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


def _latency_health(
    *,
    stream_status: str,
    frames_captured: int,
    timestamp_frames: int,
    capture_to_host_ms: float | None,
    local_source: bool = False,
) -> tuple[str, str | None]:
    if stream_status != "online":
        return "unavailable", None
    if local_source:
        return (
            "unsupported",
            "Sensor-to-host latency is unavailable for a directly connected camera.",
        )
    if frames_captured < 15:
        return "checking", None
    if timestamp_frames == 0 or capture_to_host_ms is None:
        return "timestamp_missing", LATENCY_SETUP_MESSAGE
    if capture_to_host_ms < -100 or capture_to_host_ms > 10_000:
        return (
            "unsynchronized",
            "The Pi clock appears unsynchronized. Run setup_pi_clock_sync.sh on the Pi.",
        )
    return "synchronized", None
