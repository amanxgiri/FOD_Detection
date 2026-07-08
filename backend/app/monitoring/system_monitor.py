from __future__ import annotations

from app.camera.camera_manager import CameraManager
from app.camera.types import CameraStatus
from app.inference.inference_engine import InferenceEngine


def camera_status_from_manager(camera_manager: CameraManager | None) -> str:
    if camera_manager is None:
        return CameraStatus.NOT_STARTED.value
    return camera_manager.get_status().value


def inference_status_from_engine(inference_engine: InferenceEngine | None) -> str:
    if inference_engine is None:
        return "not_started"
    return inference_engine.get_status()


def websocket_status_from_connection_count(connection_count: int) -> str:
    return "connected" if connection_count > 0 else "not_connected"
