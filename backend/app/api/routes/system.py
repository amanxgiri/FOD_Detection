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
    inference_engine = getattr(request.app.state, "inference_engine", None)
    latest_frame_age_ms = None
    if snapshot.latest_frame_timestamp is not None:
        latest_frame_age_ms = int(
            (datetime.now(UTC) - snapshot.latest_frame_timestamp).total_seconds() * 1000
        )
    active_inference_cameras = {
        camera_id
        for camera_id, model_status in runtime_statuses.model_statuses.items()
        if runtime_statuses.inference_status == "running" and model_status == "loaded"
    }

    def effective_total(camera_id: str, *, average: bool = False) -> float | None:
        capture_values = (
            snapshot.average_capture_to_host_ms_by_camera
            if average
            else snapshot.latest_capture_to_host_ms_by_camera
        )
        inference_values = (
            snapshot.average_inference_ms_by_camera
            if average
            else snapshot.latest_inference_ms_by_camera
        )
        capture_value = capture_values.get(camera_id)
        inference_value = inference_values.get(camera_id)
        value = capture_value
        if camera_id in active_inference_cameras and capture_value is not None:
            value = capture_value + (inference_value or 0.0)
        return round(value, 2) if value is not None else None

    return SystemStatusResponse(
        camera_status=runtime_statuses.camera_status,
        camera_statuses=runtime_statuses.camera_statuses,
        model_status=runtime_statuses.model_status,
        model_statuses=runtime_statuses.model_statuses,
        inference_status=runtime_statuses.inference_status,
        active_camera_id=getattr(inference_engine, "active_camera_id", None),
        scheduler_slot_count=getattr(inference_engine, "slot_count", 0),
        scheduler_missed_slots=getattr(inference_engine, "missed_slots", 0),
        backend_status="online",
        websocket_status=websocket_status_from_connection_count(
            getattr(getattr(request.app.state, "websocket_manager", None), "connection_count", 0)
        ),
        capture_fps=round(snapshot.capture_fps, 2),
        inference_fps=round(snapshot.inference_fps, 2),
        average_inference_ms=round(snapshot.average_inference_ms, 2),
        latest_frame_age_ms=latest_frame_age_ms,
        capture_to_host_ms=(
            round(snapshot.latest_capture_to_host_ms, 2)
            if snapshot.latest_capture_to_host_ms is not None
            else None
        ),
        average_capture_to_host_ms=(
            round(snapshot.average_capture_to_host_ms, 2)
            if snapshot.average_capture_to_host_ms is not None
            else None
        ),
        source_timestamp_frames=snapshot.source_timestamp_frames,
        capture_to_host_ms_by_camera={
            camera_id: (
                round(snapshot.latest_capture_to_host_ms_by_camera[camera_id], 2)
                if camera_id in snapshot.latest_capture_to_host_ms_by_camera
                else None
            )
            for camera_id in runtime_statuses.camera_statuses
        },
        average_capture_to_host_ms_by_camera={
            camera_id: (
                round(snapshot.average_capture_to_host_ms_by_camera[camera_id], 2)
                if camera_id in snapshot.average_capture_to_host_ms_by_camera
                else None
            )
            for camera_id in runtime_statuses.camera_statuses
        },
        source_timestamp_frames_by_camera={
            camera_id: snapshot.source_timestamp_frames_by_camera.get(camera_id, 0)
            for camera_id in runtime_statuses.camera_statuses
        },
        inference_ms_by_camera={
            camera_id: (
                round(snapshot.latest_inference_ms_by_camera[camera_id], 2)
                if camera_id in snapshot.latest_inference_ms_by_camera
                else None
            )
            for camera_id in runtime_statuses.camera_statuses
        },
        average_inference_ms_by_camera={
            camera_id: (
                round(snapshot.average_inference_ms_by_camera[camera_id], 2)
                if camera_id in snapshot.average_inference_ms_by_camera
                else None
            )
            for camera_id in runtime_statuses.camera_statuses
        },
        total_latency_ms_by_camera={
            camera_id: effective_total(camera_id)
            for camera_id in runtime_statuses.camera_statuses
        },
        average_total_latency_ms_by_camera={
            camera_id: effective_total(camera_id, average=True)
            for camera_id in runtime_statuses.camera_statuses
        },
        total_confirmed_detections=snapshot.confirmed_detection_count,
    )


def get_performance_monitor(request: Request) -> PerformanceMonitor:
    monitor = getattr(request.app.state, "performance_monitor", None)
    if monitor is None:
        monitor = PerformanceMonitor()
        request.app.state.performance_monitor = monitor
    return monitor
