from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.monitoring.performance_monitor import PerformanceMonitor
from app.monitoring.system_monitor import (
    camera_status_from_manager,
    inference_status_from_engine,
    websocket_status_from_connection_count,
)
from app.schemas.system import SystemStatusResponse

router = APIRouter(prefix="/system")


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(request: Request) -> SystemStatusResponse:
    monitor = get_performance_monitor(request)
    snapshot = monitor.snapshot()
    latest_frame_age_ms = None
    if snapshot.latest_frame_timestamp is not None:
        latest_frame_age_ms = int(
            (datetime.now(UTC) - snapshot.latest_frame_timestamp).total_seconds() * 1000
        )

    return SystemStatusResponse(
        camera_status=camera_status_from_manager(
            getattr(request.app.state, "camera_manager", None)
        ),
        model_status=getattr(request.app.state, "model_status", "not_started"),
        inference_status=inference_status_from_engine(
            getattr(request.app.state, "inference_engine", None)
        ),
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
