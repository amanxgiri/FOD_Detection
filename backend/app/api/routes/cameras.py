from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.api.websocket.events import make_event
from app.core.lifecycle import RuntimeCommandError, get_runtime_controller
from app.inference.model_catalog import ModelCatalog
from app.schemas.camera import (
    CameraListResponse,
    CameraModelRequest,
    CameraResponse,
    CameraUpdateRequest,
    ModelListResponse,
    ModelResponse,
)
from app.storage.models import CameraRegistration
from app.storage.repositories.camera_repository import CameraRepository

router = APIRouter()


def _camera_response(request: Request, record: CameraRegistration) -> CameraResponse:
    statuses = get_runtime_controller(request.app).get_statuses()
    return CameraResponse(
        id=record.id,
        display_name=record.display_name or record.id,
        hostname=record.id,
        rtsp_path=record.rtsp_path,
        publisher_ip=record.publisher_ip,
        stream_status=statuses.camera_statuses.get(record.id, "offline"),
        selected_model_id=record.selected_model_id,
        model_status=statuses.model_statuses.get(
            record.id, "assigned" if record.selected_model_id else "unassigned"
        ),
        discovered_at=record.discovered_at,
        last_seen_at=record.last_seen_at,
    )


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
    with request.app.state.session_factory() as session:
        CameraRepository(session).delete(camera_id)
    await request.app.state.websocket_manager.broadcast(
        make_event("camera.removed", {"camera_id": camera_id})
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
