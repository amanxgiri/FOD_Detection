from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import threading
from typing import Any

from fastapi import FastAPI

from app.camera import CameraManager, LatestFrameBuffer
from app.camera.types import CameraStatus
from app.core.logging import get_logger
from app.detection.temporal_validator import TemporalValidationConfig, TemporalValidator
from app.inference.annotated_frame_store import AnnotatedFrame, LatestAnnotatedFrameStore
from app.inference.model_adapter import ModelAdapter
from app.inference.model_loader import create_model_adapters
from app.inference.postprocessor import PostProcessor
from app.inference.renderer import FrameRenderer
from app.inference.round_robin_engine import RoundRobinInferenceEngine

logger = get_logger(__name__)
CAMERA_IDS = ("camera_1", "camera_2", "camera_3")


class RuntimeCommandError(RuntimeError):
    """Raised when an operator runtime command cannot be completed."""


@dataclass(frozen=True)
class RuntimeStatuses:
    camera_status: str
    model_status: str
    inference_status: str
    camera_statuses: dict[str, str]
    model_statuses: dict[str, str]


class RuntimeController:
    def __init__(
        self,
        app: FastAPI,
        model_adapter_factory: Any | None = None,
    ) -> None:
        self._app = app
        self._settings = app.state.settings
        self._performance_monitor = app.state.performance_monitor
        self._capture_factory = getattr(app.state, "capture_factory", None)
        self._model_adapter_factory = model_adapter_factory or create_model_adapters

        self._lock = threading.RLock()
        self._frame_buffers = {
            camera_id: LatestFrameBuffer() for camera_id in CAMERA_IDS
        }
        stores = getattr(app.state, "annotated_frame_stores", None)
        if not isinstance(stores, dict) or set(stores) != set(CAMERA_IDS):
            stores = {
                camera_id: LatestAnnotatedFrameStore() for camera_id in CAMERA_IDS
            }
            app.state.annotated_frame_stores = stores
        self._annotated_frame_stores: dict[str, LatestAnnotatedFrameStore] = stores
        self._renderer = FrameRenderer()
        self._bridge_stop_event = threading.Event()
        self._bridge_threads: dict[str, threading.Thread] = {}
        self._camera_managers = self._create_camera_managers()
        self._model_adapters: dict[str, ModelAdapter] = {}
        self._inference_engine: RoundRobinInferenceEngine | None = None
        self._model_statuses = {camera_id: "not_started" for camera_id in CAMERA_IDS}
        self._inference_status = "not_started"

        self._publish_compatibility_state()

    @property
    def camera_manager(self) -> CameraManager:
        return self._camera_managers[CAMERA_IDS[0]]

    @property
    def camera_managers(self) -> dict[str, CameraManager]:
        return self._camera_managers

    @property
    def inference_engine(self) -> RoundRobinInferenceEngine | None:
        return self._inference_engine

    @property
    def frame_buffer(self) -> LatestFrameBuffer:
        return self._frame_buffers[CAMERA_IDS[0]]

    @property
    def frame_buffers(self) -> dict[str, LatestFrameBuffer]:
        return self._frame_buffers

    def start(self, auto_start_camera: bool = True) -> None:
        self._ensure_bridges_running()
        if auto_start_camera:
            self.start_camera()

    def shutdown(self) -> None:
        self.stop_inference()
        self.stop_camera()
        self._bridge_stop_event.set()
        for thread in self._bridge_threads.values():
            thread.join(timeout=5)
        self._bridge_threads.clear()
        logger.info("three-camera runtime stopped")

    def start_camera(self) -> None:
        with self._lock:
            for manager in self._camera_managers.values():
                manager.start()
        logger.info("three-camera runtime start requested")

    def stop_camera(self) -> None:
        self.stop_inference()
        with self._lock:
            for manager in self._camera_managers.values():
                manager.stop()
        logger.info("three-camera runtime stop requested")

    def start_inference(self) -> None:
        with self._lock:
            if self._inference_engine is not None and self._inference_engine.is_running():
                return
            offline = [
                camera_id
                for camera_id, manager in self._camera_managers.items()
                if not manager.is_running()
                or manager.get_status() != CameraStatus.ONLINE
            ]
            if offline:
                raise RuntimeCommandError(
                    "all three cameras must be running before inference starts"
                )

            self._model_statuses = {camera_id: "loading" for camera_id in CAMERA_IDS}
            self._inference_status = "starting"
            adapters: dict[str, ModelAdapter] = {}
            try:
                adapters = self._create_model_adapter_mapping()
                for camera_id in CAMERA_IDS:
                    adapters[camera_id].load()
                    adapters[camera_id].warmup()
                    self._model_statuses[camera_id] = "loaded"
                engine = self._create_inference_engine(adapters)
                engine.start()
            except Exception as exc:
                for adapter in _unique_adapters(adapters):
                    adapter.close()
                self._model_adapters = {}
                self._inference_engine = None
                self._app.state.inference_engine = None
                self._model_statuses = {camera_id: "error" for camera_id in CAMERA_IDS}
                self._inference_status = "error"
                raise RuntimeCommandError(str(exc)) from exc

            self._model_adapters = adapters
            self._inference_engine = engine
            self._app.state.inference_engine = engine
            self._inference_status = "running"
        logger.info("round-robin inference runtime started")

    def stop_inference(self) -> None:
        with self._lock:
            engine = self._inference_engine
            adapters = self._model_adapters
            self._inference_engine = None
            self._model_adapters = {}
            self._app.state.inference_engine = None

            if engine is not None:
                engine.stop()
            for adapter in _unique_adapters(adapters):
                adapter.close()

            if (
                self._inference_status != "not_started"
                or any(value in {"loaded", "loading", "error"} for value in self._model_statuses.values())
            ):
                self._inference_status = "stopped"
                self._model_statuses = {camera_id: "unloaded" for camera_id in CAMERA_IDS}
        logger.info("round-robin inference runtime stopped")

    def get_statuses(self) -> RuntimeStatuses:
        with self._lock:
            camera_statuses = {
                camera_id: manager.get_status().value
                for camera_id, manager in self._camera_managers.items()
            }
            return RuntimeStatuses(
                camera_status=_aggregate_camera_status(camera_statuses),
                model_status=_aggregate_model_status(self._model_statuses),
                inference_status=self._effective_inference_status(),
                camera_statuses=camera_statuses,
                model_statuses=dict(self._model_statuses),
            )

    def _effective_inference_status(self) -> str:
        if self._inference_engine is None:
            return self._inference_status
        engine_status = self._inference_engine.get_status()
        if engine_status in {"running", "error"}:
            return engine_status
        return self._inference_status

    def _create_camera_managers(self) -> dict[str, CameraManager]:
        return {
            camera_id: CameraManager(
                source=source,
                camera_id=camera_id,
                frame_buffer=self._frame_buffers[camera_id],
                reconnect_delay_seconds=self._settings.camera_reconnect_delay_seconds,
                capture_factory=self._capture_factory,
                performance_monitor=self._performance_monitor,
            )
            for camera_id, source in self._settings.camera_sources.items()
        }

    def _create_model_adapter_mapping(self) -> dict[str, ModelAdapter]:
        created = self._model_adapter_factory(self._settings)
        if isinstance(created, Mapping):
            adapters = dict(created)
            if set(adapters) != set(CAMERA_IDS):
                raise RuntimeCommandError(
                    "model adapter factory must provide camera_1, camera_2, and camera_3"
                )
            return adapters
        # Compatibility for test/development factories that return one adapter.
        return {camera_id: created for camera_id in CAMERA_IDS}

    def _create_inference_engine(
        self,
        adapters: dict[str, ModelAdapter],
    ) -> RoundRobinInferenceEngine:
        validator_config = TemporalValidationConfig(
            enabled=self._settings.temporal_validation_enabled,
            window_size=self._settings.temporal_window_size,
            required_hits=self._settings.temporal_required_hits,
            match_iou=self._settings.temporal_match_iou,
        )
        return RoundRobinInferenceEngine(
            frame_buffers=self._frame_buffers,
            model_adapters=adapters,
            annotated_frame_stores=self._annotated_frame_stores,
            postprocessor=PostProcessor(
                confidence_threshold=self._settings.model_confidence_threshold
            ),
            performance_monitor=self._performance_monitor,
            frame_renderer=FrameRenderer(),
            temporal_validators={
                camera_id: TemporalValidator(validator_config)
                for camera_id in CAMERA_IDS
            },
            slot_timeout_seconds=self._settings.inference_slot_timeout_seconds,
        )

    def _ensure_bridges_running(self) -> None:
        with self._lock:
            self._bridge_stop_event.clear()
            for camera_id in CAMERA_IDS:
                current = self._bridge_threads.get(camera_id)
                if current is not None and current.is_alive():
                    continue
                thread = threading.Thread(
                    target=_publish_camera_frames,
                    kwargs={
                        "frame_buffer": self._frame_buffers[camera_id],
                        "renderer": self._renderer,
                        "annotated_frame_store": self._annotated_frame_stores[camera_id],
                        "stop_event": self._bridge_stop_event,
                        "should_publish": self._should_publish_raw_frames,
                    },
                    name=f"camera-frame-publisher-{camera_id}",
                    daemon=True,
                )
                self._bridge_threads[camera_id] = thread
                thread.start()

    def _should_publish_raw_frames(self) -> bool:
        with self._lock:
            return self._effective_inference_status() != "running"

    def _publish_compatibility_state(self) -> None:
        self._app.state.frame_buffers = self._frame_buffers
        self._app.state.camera_managers = self._camera_managers
        self._app.state.frame_buffer = self._frame_buffers[CAMERA_IDS[0]]
        self._app.state.camera_manager = self._camera_managers[CAMERA_IDS[0]]
        self._app.state.annotated_frame_store = self._annotated_frame_stores[CAMERA_IDS[0]]


def start_live_runtime(app: FastAPI) -> None:
    controller = get_runtime_controller(app)
    controller.start(auto_start_camera=True)
    logger.info("three-camera live runtime started")


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

    managers = getattr(app.state, "camera_managers", {})
    camera_statuses = {
        camera_id: managers[camera_id].get_status().value
        if camera_id in managers
        else CameraStatus.NOT_STARTED.value
        for camera_id in CAMERA_IDS
    }
    model_statuses = {
        camera_id: "not_started" for camera_id in CAMERA_IDS
    }
    return RuntimeStatuses(
        camera_status=_aggregate_camera_status(camera_statuses),
        model_status="not_started",
        inference_status="not_started",
        camera_statuses=camera_statuses,
        model_statuses=model_statuses,
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
        annotated_frame_store.publish(
            AnnotatedFrame(
                sequence_id=packet.sequence_id,
                captured_at=packet.captured_at,
                frame=renderer.render(packet.frame, detections=[]),
            )
        )
        last_sequence_id = packet.sequence_id


def _unique_adapters(adapters: Mapping[str, ModelAdapter]) -> list[ModelAdapter]:
    unique: list[ModelAdapter] = []
    seen: set[int] = set()
    for adapter in adapters.values():
        identity = id(adapter)
        if identity not in seen:
            seen.add(identity)
            unique.append(adapter)
    return unique


def _aggregate_camera_status(statuses: Mapping[str, str]) -> str:
    values = set(statuses.values())
    if values == {CameraStatus.ONLINE.value}:
        return CameraStatus.ONLINE.value
    if values == {CameraStatus.STOPPED.value}:
        return CameraStatus.STOPPED.value
    if CameraStatus.DEGRADED.value in values or CameraStatus.OFFLINE.value in values:
        return CameraStatus.DEGRADED.value
    if CameraStatus.OPENING.value in values:
        return CameraStatus.OPENING.value
    return CameraStatus.NOT_STARTED.value


def _aggregate_model_status(statuses: Mapping[str, str]) -> str:
    values = set(statuses.values())
    if len(values) == 1:
        return next(iter(values))
    if "error" in values:
        return "error"
    if "loading" in values:
        return "loading"
    return "partial"
