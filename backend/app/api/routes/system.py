from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.core.lifecycle import runtime_statuses_from_app
from app.monitoring.performance_monitor import PerformanceMonitor
from app.monitoring.system_monitor import (
    websocket_status_from_connection_count,
)
from app.schemas.system import SystemStatusResponse

router = APIRouter(prefix="/system")


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(request: Request) -> SystemStatusResponse:
    return build_system_status_response(request)


def build_system_status_response(request: Request) -> SystemStatusResponse:
    monitor = get_performance_monitor(request)
    snapshot = monitor.snapshot()
    runtime_statuses = runtime_statuses_from_app(request.app)
    latest_frame_age_ms = None
    if snapshot.latest_frame_timestamp is not None:
        latest_frame_age_ms = int(
            (datetime.now(UTC) - snapshot.latest_frame_timestamp).total_seconds() * 1000
        )

    return SystemStatusResponse(
        camera_status=runtime_statuses.camera_status,
        model_status=runtime_statuses.model_status,
        inference_status=runtime_statuses.inference_status,
        backend_status="online",
        websocket_status=websocket_status_from_connection_count(
            getattr(getattr(request.app.state, "websocket_manager", None), "connection_count", 0)
        ),
        capture_fps=round(snapshot.capture_fps, 2),
        inference_fps=round(snapshot.inference_fps, 2),
        average_inference_ms=round(snapshot.average_inference_ms, 2),
        latest_frame_age_ms=latest_frame_age_ms,
        total_confirmed_detections=snapshot.confirmed_detection_count,
    )


def get_performance_monitor(request: Request) -> PerformanceMonitor:
    monitor = getattr(request.app.state, "performance_monitor", None)
    if monitor is None:
        monitor = PerformanceMonitor()
        request.app.state.performance_monitor = monitor
    return monitor
