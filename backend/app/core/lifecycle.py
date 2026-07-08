from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI

from app.camera import CameraManager, LatestFrameBuffer
from app.core.logging import get_logger
from app.inference.annotated_frame_store import AnnotatedFrame
from app.inference.renderer import FrameRenderer

logger = get_logger(__name__)


def start_live_runtime(app: FastAPI) -> None:
    if getattr(app.state, "camera_manager", None) is not None:
        return

    settings = app.state.settings
    frame_buffer = LatestFrameBuffer()
    renderer = FrameRenderer()
    stop_event = threading.Event()
    capture_factory = getattr(app.state, "capture_factory", None)

    camera_manager = CameraManager(
        source=settings.camera_source,
        frame_buffer=frame_buffer,
        reconnect_delay_seconds=settings.camera_reconnect_delay_seconds,
        capture_factory=capture_factory,
        performance_monitor=app.state.performance_monitor,
    )
    bridge_thread = threading.Thread(
        target=_publish_camera_frames,
        kwargs={
            "frame_buffer": frame_buffer,
            "renderer": renderer,
            "annotated_frame_store": app.state.annotated_frame_store,
            "stop_event": stop_event,
        },
        name="camera-frame-publisher",
        daemon=True,
    )

    app.state.frame_buffer = frame_buffer
    app.state.camera_manager = camera_manager
    app.state.live_runtime_stop_event = stop_event
    app.state.live_runtime_thread = bridge_thread

    bridge_thread.start()
    camera_manager.start()
    logger.info("live camera runtime started")


def stop_live_runtime(app: FastAPI) -> None:
    stop_event = getattr(app.state, "live_runtime_stop_event", None)
    if stop_event is not None:
        stop_event.set()

    camera_manager = getattr(app.state, "camera_manager", None)
    if camera_manager is not None:
        camera_manager.stop()

    bridge_thread = getattr(app.state, "live_runtime_thread", None)
    if bridge_thread is not None:
        bridge_thread.join(timeout=5)

    logger.info("live camera runtime stopped")


def _publish_camera_frames(
    frame_buffer: LatestFrameBuffer,
    renderer: FrameRenderer,
    annotated_frame_store: Any,
    stop_event: threading.Event,
) -> None:
    last_sequence_id = -1
    while not stop_event.is_set():
        packet = frame_buffer.wait_for_newer(last_sequence_id, timeout=0.5)
        if packet is None:
            continue
        annotated = renderer.render(packet.frame, detections=[])
        annotated_frame_store.publish(
            AnnotatedFrame(
                sequence_id=packet.sequence_id,
                captured_at=packet.captured_at,
                frame=annotated,
            )
        )
        last_sequence_id = packet.sequence_id
