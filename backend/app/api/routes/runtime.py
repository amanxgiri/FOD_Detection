from fastapi import APIRouter, HTTPException, Request

from app.api.routes.system import build_system_status_response
from app.core.lifecycle import RuntimeCommandError, get_runtime_controller
from app.schemas.system import SystemStatusResponse

router = APIRouter(prefix="/runtime")


@router.post("/camera/start", response_model=SystemStatusResponse)
def start_camera(request: Request) -> SystemStatusResponse:
    controller = get_runtime_controller(request.app)
    controller.start(auto_start_camera=False)
    try:
        controller.start_camera()
    except RuntimeCommandError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return build_system_status_response(request)


@router.post("/camera/stop", response_model=SystemStatusResponse)
def stop_camera(request: Request) -> SystemStatusResponse:
    controller = get_runtime_controller(request.app)
    controller.stop_camera()
    return build_system_status_response(request)


@router.post("/inference/start", response_model=SystemStatusResponse)
def start_inference(request: Request) -> SystemStatusResponse:
    controller = get_runtime_controller(request.app)
    try:
        controller.start_inference()
    except RuntimeCommandError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return build_system_status_response(request)


@router.post("/inference/stop", response_model=SystemStatusResponse)
def stop_inference(request: Request) -> SystemStatusResponse:
    controller = get_runtime_controller(request.app)
    controller.stop_inference()
    return build_system_status_response(request)
