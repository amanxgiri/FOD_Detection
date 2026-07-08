from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import threading
from typing import Any

from fastapi import FastAPI

from app.camera import CameraManager, LatestFrameBuffer
from app.camera.types import CameraStatus
from app.core.logging import get_logger
from app.detection.temporal_validator import TemporalValidationConfig, TemporalValidator
from app.inference.annotated_frame_store import AnnotatedFrame
from app.inference.inference_engine import InferenceEngine
from app.inference.model_adapter import ModelAdapter
from app.inference.model_loader import create_model_adapter
from app.inference.postprocessor import PostProcessor
from app.inference.renderer import FrameRenderer

logger = get_logger(__name__)


class RuntimeCommandError(RuntimeError):
    """Raised when an operator runtime command cannot be completed."""


@dataclass(frozen=True)
class RuntimeStatuses:
    camera_status: str
    model_status: str
    inference_status: str


class RuntimeController:
    def __init__(
        self,
        app: FastAPI,
        model_adapter_factory: Any | None = None,
    ) -> None:
        self._app = app
        self._settings = app.state.settings
        self._annotated_frame_store = app.state.annotated_frame_store
        self._performance_monitor = app.state.performance_monitor
        self._capture_factory = getattr(app.state, "capture_factory", None)
        self._model_adapter_factory = model_adapter_factory or create_model_adapter

        self._lock = threading.RLock()
        self._frame_buffer = LatestFrameBuffer()
        self._renderer = FrameRenderer()
        self._bridge_stop_event = threading.Event()
        self._bridge_thread: threading.Thread | None = None
        self._camera_manager = self._create_camera_manager()
        self._model_adapter: ModelAdapter | None = None
        self._inference_engine: InferenceEngine | None = None
        self._model_status = "not_started"
        self._inference_status = "not_started"

        self._app.state.frame_buffer = self._frame_buffer
        self._app.state.camera_manager = self._camera_manager

    @property
    def camera_manager(self) -> CameraManager:
        return self._camera_manager

    @property
    def inference_engine(self) -> InferenceEngine | None:
        return self._inference_engine

    @property
    def frame_buffer(self) -> LatestFrameBuffer:
        return self._frame_buffer

    def start(self, auto_start_camera: bool = True) -> None:
        self._ensure_bridge_running()
        if auto_start_camera:
            self.start_camera()

    def shutdown(self) -> None:
        self.stop_inference()
        self.stop_camera()
        self._bridge_stop_event.set()
        bridge_thread = self._bridge_thread
        if bridge_thread is not None:
            bridge_thread.join(timeout=5)
        logger.info("live camera runtime stopped")

    def start_camera(self) -> None:
        with self._lock:
            if self._camera_manager.is_running():
                return
            self._camera_manager.start()
        logger.info("camera runtime start requested")

    def stop_camera(self) -> None:
        with self._lock:
            self._camera_manager.stop()
        logger.info("camera runtime stop requested")

    def start_inference(self) -> None:
        with self._lock:
            if self._inference_engine is not None and self._inference_engine.is_running():
                return
            if not self._camera_manager.is_running():
                raise RuntimeCommandError("camera must be running before inference starts")

            self._model_status = "loading"
            self._inference_status = "starting"
            adapter: ModelAdapter | None = None
            try:
                adapter = self._model_adapter_factory(self._settings)
                adapter.load()
                adapter.warmup()
                engine = self._create_inference_engine(adapter)
                engine.start()
            except Exception as exc:
                if adapter is not None:
                    adapter.close()
                self._model_adapter = None
                self._inference_engine = None
                self._app.state.inference_engine = None
                self._model_status = "error"
                self._inference_status = "error"
                raise RuntimeCommandError(str(exc)) from exc

            self._model_adapter = adapter
            self._inference_engine = engine
            self._app.state.inference_engine = engine
            self._model_status = "loaded"
            self._inference_status = "running"
        logger.info("inference runtime started")

    def stop_inference(self) -> None:
        with self._lock:
            engine = self._inference_engine
            adapter = self._model_adapter
            self._inference_engine = None
            self._model_adapter = None
            self._app.state.inference_engine = None

            if engine is not None:
                engine.stop()
            if adapter is not None:
                adapter.close()

            if (
                self._inference_status != "not_started"
                or self._model_status in {"loaded", "loading", "error"}
            ):
                self._inference_status = "stopped"
                self._model_status = "unloaded"
        logger.info("inference runtime stopped")

    def get_statuses(self) -> RuntimeStatuses:
        with self._lock:
            return RuntimeStatuses(
                camera_status=self._camera_manager.get_status().value,
                model_status=self._model_status,
                inference_status=self._effective_inference_status(),
            )

    def _effective_inference_status(self) -> str:
        if self._inference_engine is None:
            return self._inference_status
        engine_status = self._inference_engine.get_status()
        if engine_status == "running":
            return "running"
        if engine_status == "error":
            return "error"
        return self._inference_status

    def _create_camera_manager(self) -> CameraManager:
        return CameraManager(
            source=self._settings.camera_source,
            frame_buffer=self._frame_buffer,
            reconnect_delay_seconds=self._settings.camera_reconnect_delay_seconds,
            capture_factory=self._capture_factory,
            performance_monitor=self._performance_monitor,
        )

    def _create_inference_engine(self, adapter: ModelAdapter) -> InferenceEngine:
        return InferenceEngine(
            frame_buffer=self._frame_buffer,
            model_adapter=adapter,
            postprocessor=PostProcessor(
                confidence_threshold=self._settings.model_confidence_threshold
            ),
            performance_monitor=self._performance_monitor,
            frame_renderer=FrameRenderer(),
            annotated_frame_store=self._annotated_frame_store,
            temporal_validator=TemporalValidator(
                TemporalValidationConfig(
                    enabled=self._settings.temporal_validation_enabled,
                    window_size=self._settings.temporal_window_size,
                    required_hits=self._settings.temporal_required_hits,
                    match_iou=self._settings.temporal_match_iou,
                )
            ),
        )

    def _ensure_bridge_running(self) -> None:
        with self._lock:
            if self._bridge_thread is not None and self._bridge_thread.is_alive():
                return
            self._bridge_stop_event.clear()
            self._bridge_thread = threading.Thread(
                target=_publish_camera_frames,
                kwargs={
                    "frame_buffer": self._frame_buffer,
                    "renderer": self._renderer,
                    "annotated_frame_store": self._annotated_frame_store,
                    "stop_event": self._bridge_stop_event,
                    "should_publish": self._should_publish_raw_frames,
                },
                name="camera-frame-publisher",
                daemon=True,
            )
            self._bridge_thread.start()

    def _should_publish_raw_frames(self) -> bool:
        with self._lock:
            return self._effective_inference_status() != "running"


def start_live_runtime(app: FastAPI) -> None:
    controller = get_runtime_controller(app)
    controller.start(auto_start_camera=True)
    logger.info("live camera runtime started")


def get_runtime_controller(app: FastAPI) -> RuntimeController:
    controller = getattr(app.state, "runtime_controller", None)
    if controller is None:
        controller = RuntimeController(
            app,
            model_adapter_factory=getattr(app.state, "model_adapter_factory", None),
        )
        app.state.runtime_controller = controller
    return controller


def runtime_statuses_from_app(app: FastAPI) -> RuntimeStatuses:
    controller = getattr(app.state, "runtime_controller", None)
    if controller is not None:
        return controller.get_statuses()

    camera_manager = getattr(app.state, "camera_manager", None)
    camera_status = (
        camera_manager.get_status().value
        if camera_manager is not None
        else CameraStatus.NOT_STARTED.value
    )
    return RuntimeStatuses(
        camera_status=camera_status,
        model_status=getattr(app.state, "model_status", "not_started"),
        inference_status="not_started",
    )


def stop_live_runtime(app: FastAPI) -> None:
    controller = getattr(app.state, "runtime_controller", None)
    if controller is not None:
        controller.shutdown()


def _publish_camera_frames(
    frame_buffer: LatestFrameBuffer,
    renderer: FrameRenderer,
    annotated_frame_store: Any,
    stop_event: threading.Event,
    should_publish: Callable[[], bool] | None = None,
) -> None:
    last_sequence_id = -1
    while not stop_event.is_set():
        packet = frame_buffer.wait_for_newer(last_sequence_id, timeout=0.5)
        if packet is None:
            continue
        if should_publish is not None and not should_publish():
            last_sequence_id = packet.sequence_id
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
