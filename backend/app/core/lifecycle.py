from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import threading
from typing import Any

from fastapi import FastAPI

from app.camera import CameraManager, LatestFrameBuffer
from app.camera.opencv_capture import configure_ffmpeg_capture_options
from app.camera.types import CameraStatus
from app.core.logging import get_logger
from app.detection.temporal_validator import TemporalValidationConfig, TemporalValidator
from app.inference.annotated_frame_store import AnnotatedFrame, LatestAnnotatedFrameStore
from app.inference.model_adapter import ModelAdapter
from app.inference.model_catalog import ModelCatalog
from app.inference.model_pool import ModelPool
from app.inference.postprocessor import PostProcessor
from app.inference.renderer import FrameRenderer
from app.inference.round_robin_engine import RoundRobinInferenceEngine
from app.storage.repositories.camera_repository import CameraRepository

logger = get_logger(__name__)


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
    def __init__(self, app: FastAPI, model_adapter_factory: Any | None = None) -> None:
        self._app = app
        self._settings = app.state.settings
        self._performance_monitor = app.state.performance_monitor
        self._capture_factory = getattr(app.state, "capture_factory", None)
        self._model_adapter_factory = model_adapter_factory
        configure_ffmpeg_capture_options(self._settings.camera_ffmpeg_capture_options)

        self._lock = threading.RLock()
        self._frame_buffers: dict[str, LatestFrameBuffer] = {}
        self._annotated_frame_stores: dict[str, LatestAnnotatedFrameStore] = {}
        self._camera_managers: dict[str, CameraManager] = {}
        self._camera_sources: dict[str, str] = {}
        self._model_assignments: dict[str, str | None] = {}
        self._model_statuses: dict[str, str] = {}
        self._renderer = FrameRenderer()
        self._bridge_threads: dict[str, threading.Thread] = {}
        self._bridge_stop_events: dict[str, threading.Event] = {}
        self._inference_engine: RoundRobinInferenceEngine | None = None
        self._model_adapters: dict[str, ModelAdapter] = {}
        self._inference_status = "not_started"
        self._cameras_enabled = True
        self._catalog = getattr(app.state, "model_catalog", None) or ModelCatalog(
            self._settings.model_catalog_directory
        )
        app.state.model_catalog = self._catalog
        self._model_pool = ModelPool(self._settings, self._catalog)

        self._load_registered_cameras()
        self._publish_state()

    @property
    def camera_manager(self) -> CameraManager | None:
        return next(iter(self._camera_managers.values()), None)

    @property
    def camera_managers(self) -> dict[str, CameraManager]:
        return self._camera_managers

    @property
    def inference_engine(self) -> RoundRobinInferenceEngine | None:
        return self._inference_engine

    @property
    def frame_buffer(self) -> LatestFrameBuffer | None:
        return next(iter(self._frame_buffers.values()), None)

    @property
    def frame_buffers(self) -> dict[str, LatestFrameBuffer]:
        return self._frame_buffers

    def start(self, auto_start_camera: bool = True) -> None:
        if auto_start_camera:
            self.start_camera()

    def shutdown(self) -> None:
        self.stop_camera()
        for stop_event in self._bridge_stop_events.values():
            stop_event.set()
        for thread in self._bridge_threads.values():
            thread.join(timeout=2)
        self._bridge_threads.clear()
        self._bridge_stop_events.clear()
        logger.info("dynamic camera runtime stopped")

    def start_camera(self) -> None:
        with self._lock:
            self._cameras_enabled = True
            for camera_id, manager in self._camera_managers.items():
                self._ensure_bridge_running(camera_id)
                manager.start()
        logger.info("dynamic camera runtime start requested")

    def stop_camera(self) -> None:
        self.stop_inference()
        with self._lock:
            self._cameras_enabled = False
            managers = list(self._camera_managers.values())
        for manager in managers:
            manager.stop()
        logger.info("dynamic camera runtime stop requested")

    def add_camera(
        self,
        camera_id: str,
        rtsp_path: str,
        selected_model_id: str | None = None,
        source_override: str | None = None,
    ) -> bool:
        with self._lock:
            if camera_id in self._camera_managers:
                if self._model_assignments.get(camera_id) != selected_model_id:
                    self._model_assignments[camera_id] = selected_model_id
                    self._refresh_unloaded_model_status(camera_id)
                return False
            source = source_override or (
                f"{self._settings.mediamtx_rtsp_url.rstrip('/')}/{rtsp_path}"
            )
            frame_buffer = LatestFrameBuffer()
            store = LatestAnnotatedFrameStore()
            manager = CameraManager(
                source=source,
                camera_id=camera_id,
                frame_buffer=frame_buffer,
                reconnect_delay_seconds=self._settings.camera_reconnect_delay_seconds,
                capture_factory=self._capture_factory,
                capture_open_timeout_ms=self._settings.camera_capture_open_timeout_ms,
                capture_read_timeout_ms=self._settings.camera_capture_read_timeout_ms,
                capture_buffer_size=self._settings.camera_capture_buffer_size,
                capture_decoder_threads=self._settings.camera_capture_decoder_threads,
                performance_monitor=self._performance_monitor,
            )
            self._frame_buffers[camera_id] = frame_buffer
            self._annotated_frame_stores[camera_id] = store
            self._camera_managers[camera_id] = manager
            self._camera_sources[camera_id] = source
            self._model_assignments[camera_id] = selected_model_id
            self._model_statuses[camera_id] = (
                "assigned" if selected_model_id is not None else "unassigned"
            )
            self._ensure_bridge_running(camera_id)
            self._publish_state()
            if self._cameras_enabled:
                manager.start()
        return True

    def remove_camera(self, camera_id: str) -> None:
        with self._lock:
            manager = self._camera_managers.get(camera_id)
            if manager is None:
                raise RuntimeCommandError(f"unknown camera: {camera_id}")
            if manager.get_status() not in {
                CameraStatus.OFFLINE,
                CameraStatus.STOPPED,
                CameraStatus.NOT_STARTED,
            }:
                raise RuntimeCommandError("camera must be offline before it can be removed")
            if self._inference_engine is not None:
                self._inference_engine.remove_lane(camera_id)
            model_id = self._model_assignments.get(camera_id)
            if (
                camera_id in self._model_adapters
                and model_id is not None
                and self._model_adapter_factory is None
            ):
                self._model_pool.release(model_id)
            stop_event = self._bridge_stop_events.pop(camera_id, None)
            if stop_event is not None:
                stop_event.set()
            self._bridge_threads.pop(camera_id, None)
            self._camera_managers.pop(camera_id, None)
            self._frame_buffers.pop(camera_id, None)
            self._annotated_frame_stores.pop(camera_id, None)
            self._camera_sources.pop(camera_id, None)
            self._model_assignments.pop(camera_id, None)
            self._model_statuses.pop(camera_id, None)
            self._model_adapters.pop(camera_id, None)
            self._publish_state()

    def set_model_assignment(self, camera_id: str, model_id: str | None) -> None:
        with self._lock:
            if camera_id not in self._camera_managers:
                raise RuntimeCommandError(f"unknown camera: {camera_id}")
            if model_id is not None and self._catalog.get(model_id) is None:
                raise RuntimeCommandError(f"unknown or unavailable model: {model_id}")
            previous_model_id = self._model_assignments.get(camera_id)
            if previous_model_id == model_id:
                return
            engine = self._inference_engine
            if engine is None or not engine.is_running():
                self._model_assignments[camera_id] = model_id
                self._model_statuses[camera_id] = (
                    "assigned" if model_id is not None else "unassigned"
                )
                return
            if self._camera_managers[camera_id].get_status() != CameraStatus.ONLINE:
                if camera_id in self._model_adapters:
                    engine.remove_lane(camera_id)
                    self._model_adapters.pop(camera_id, None)
                    if previous_model_id is not None and self._model_adapter_factory is None:
                        self._model_pool.release(previous_model_id)
                self._model_assignments[camera_id] = model_id
                self._model_statuses[camera_id] = (
                    "assigned" if model_id is not None else "unassigned"
                )
                return
            if model_id is None:
                engine.remove_lane(camera_id)
                self._model_assignments[camera_id] = None
                self._model_adapters.pop(camera_id, None)
                if previous_model_id is not None and self._model_adapter_factory is None:
                    self._model_pool.release(previous_model_id)
                self._model_statuses[camera_id] = "unassigned"
                return
            previous_status = self._model_statuses[camera_id]
            self._model_statuses[camera_id] = "loading"
        try:
            adapter = self._acquire_adapter(camera_id, model_id)
            engine.upsert_lane(
                camera_id,
                self._frame_buffers[camera_id],
                adapter,
                self._annotated_frame_stores[camera_id],
                self._new_validator(),
            )
        except Exception as exc:
            with self._lock:
                self._model_statuses[camera_id] = previous_status
            raise RuntimeCommandError(str(exc)) from exc
        with self._lock:
            self._model_assignments[camera_id] = model_id
            self._model_adapters[camera_id] = adapter
            self._model_statuses[camera_id] = "loaded"
            if previous_model_id is not None and self._model_adapter_factory is None:
                self._model_pool.release(previous_model_id)

    def set_camera_online(self, camera_id: str, online: bool) -> None:
        """Add or remove an assigned inference lane as publisher state changes."""
        with self._lock:
            engine = self._inference_engine
            model_id = self._model_assignments.get(camera_id)
            if engine is None or not engine.is_running() or model_id is None:
                return
            if not online:
                engine.remove_lane(camera_id)
                self._model_adapters.pop(camera_id, None)
                if self._model_adapter_factory is None:
                    self._model_pool.release(model_id)
                self._model_statuses[camera_id] = "assigned"
                return
            if camera_id in self._model_adapters:
                return
            self._model_statuses[camera_id] = "loading"
        try:
            adapter = self._acquire_adapter(camera_id, model_id)
            engine.upsert_lane(
                camera_id,
                self._frame_buffers[camera_id],
                adapter,
                self._annotated_frame_stores[camera_id],
                self._new_validator(),
            )
        except Exception as exc:
            with self._lock:
                self._model_statuses[camera_id] = "error"
            raise RuntimeCommandError(str(exc)) from exc
        with self._lock:
            self._model_adapters[camera_id] = adapter
            self._model_statuses[camera_id] = "loaded"

    def start_inference(self) -> None:
        with self._lock:
            if self._inference_engine is not None and self._inference_engine.is_running():
                return
            assignments = {
                camera_id: model_id
                for camera_id, model_id in self._model_assignments.items()
                if model_id is not None
                and self._camera_managers[camera_id].get_status() == CameraStatus.ONLINE
            }
            if not assignments:
                raise RuntimeCommandError(
                    "at least one online camera must have an assigned model"
                )
            self._inference_status = "starting"
            for camera_id in assignments:
                self._model_statuses[camera_id] = "loading"

        adapters: dict[str, ModelAdapter] = {}
        try:
            for camera_id, model_id in assignments.items():
                adapters[camera_id] = self._acquire_adapter(camera_id, model_id)
            engine = self._create_inference_engine(adapters)
            engine.start()
        except Exception as exc:
            with self._lock:
                for camera_id in assignments:
                    self._model_statuses[camera_id] = "error"
                self._inference_status = "error"
            raise RuntimeCommandError(str(exc)) from exc

        with self._lock:
            self._model_adapters = adapters
            self._inference_engine = engine
            self._app.state.inference_engine = engine
            for camera_id in assignments:
                self._model_statuses[camera_id] = "loaded"
            self._inference_status = "running"
        logger.info("dynamic round-robin inference runtime started")

    def stop_inference(self) -> None:
        with self._lock:
            engine = self._inference_engine
            adapters = list({id(adapter): adapter for adapter in self._model_adapters.values()}.values())
            self._inference_engine = None
            self._model_adapters = {}
            self._app.state.inference_engine = None
        if engine is not None:
            engine.stop()
        if self._model_adapter_factory is None:
            self._model_pool.close_all()
        else:
            for adapter in adapters:
                adapter.close()
        with self._lock:
            if self._inference_status != "not_started":
                self._inference_status = "stopped"
            for camera_id in self._model_statuses:
                self._refresh_unloaded_model_status(camera_id)
        logger.info("dynamic round-robin inference runtime stopped")

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

    def get_model_assignment(self, camera_id: str) -> str | None:
        with self._lock:
            return self._model_assignments.get(camera_id)

    def _load_registered_cameras(self) -> None:
        session_factory = getattr(self._app.state, "session_factory", None)
        records = []
        if session_factory is not None:
            with session_factory() as session:
                records = CameraRepository(session).list_all()
        for record in records:
            self.add_camera(record.id, record.rtsp_path, record.selected_model_id)
        if not records and self._capture_factory is not None:
            for index, (camera_id, source) in enumerate(
                self._settings.camera_sources.items(), start=1
            ):
                self.add_camera(
                    camera_id,
                    camera_id,
                    f"model_{index}",
                    source_override=source,
                )

    def _acquire_adapter(self, camera_id: str, model_id: str) -> ModelAdapter:
        if self._model_adapter_factory is None:
            return self._model_pool.acquire(model_id)
        created = self._model_adapter_factory(self._settings)
        adapter = created.get(camera_id) if isinstance(created, Mapping) else created
        if adapter is None:
            raise RuntimeCommandError(f"model adapter factory has no lane for {camera_id}")
        adapter.load()
        adapter.warmup()
        return adapter

    def _create_inference_engine(
        self, adapters: dict[str, ModelAdapter]
    ) -> RoundRobinInferenceEngine:
        return RoundRobinInferenceEngine(
            frame_buffers=self._frame_buffers,
            model_adapters=adapters,
            annotated_frame_stores=self._annotated_frame_stores,
            postprocessor=PostProcessor(
                confidence_threshold=self._settings.model_confidence_threshold
            ),
            performance_monitor=self._performance_monitor,
            frame_renderer=FrameRenderer(),
            temporal_validators={camera_id: self._new_validator() for camera_id in adapters},
            idle_backoff_seconds=self._settings.inference_idle_backoff_seconds,
        )

    def _new_validator(self) -> TemporalValidator:
        return TemporalValidator(
            TemporalValidationConfig(
                enabled=self._settings.temporal_validation_enabled,
                window_size=self._settings.temporal_window_size,
                required_hits=self._settings.temporal_required_hits,
                match_iou=self._settings.temporal_match_iou,
            )
        )

    def _ensure_bridge_running(self, camera_id: str) -> None:
        current = self._bridge_threads.get(camera_id)
        if current is not None and current.is_alive():
            return
        stop_event = threading.Event()
        thread = threading.Thread(
            target=_publish_camera_frames,
            kwargs={
                "camera_id": camera_id,
                "frame_buffer": self._frame_buffers[camera_id],
                "renderer": self._renderer,
                "annotated_frame_store": self._annotated_frame_stores[camera_id],
                "stop_event": stop_event,
                "should_publish": self._should_publish_raw_frame,
            },
            name=f"camera-frame-publisher-{camera_id}",
            daemon=True,
        )
        self._bridge_stop_events[camera_id] = stop_event
        self._bridge_threads[camera_id] = thread
        thread.start()

    def _should_publish_raw_frame(self, camera_id: str) -> bool:
        with self._lock:
            return not (
                self._effective_inference_status() == "running"
                and camera_id in self._model_adapters
            )

    def _effective_inference_status(self) -> str:
        if self._inference_engine is None:
            return self._inference_status
        status = self._inference_engine.get_status()
        return status if status in {"running", "error"} else self._inference_status

    def _refresh_unloaded_model_status(self, camera_id: str) -> None:
        if not self._model_assignments.get(camera_id):
            self._model_statuses[camera_id] = "unassigned"
        elif self._inference_status == "stopped":
            self._model_statuses[camera_id] = "unloaded"
        else:
            self._model_statuses[camera_id] = "assigned"

    def _publish_state(self) -> None:
        self._app.state.frame_buffers = self._frame_buffers
        self._app.state.camera_managers = self._camera_managers
        self._app.state.annotated_frame_stores = self._annotated_frame_stores
        self._app.state.frame_buffer = self.frame_buffer
        self._app.state.camera_manager = self.camera_manager
        self._app.state.annotated_frame_store = next(
            iter(self._annotated_frame_stores.values()), None
        )


def start_live_runtime(app: FastAPI) -> None:
    controller = get_runtime_controller(app)
    controller.start(auto_start_camera=True)
    logger.info("dynamic camera live runtime started")


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
        camera_id: manager.get_status().value for camera_id, manager in managers.items()
    }
    return RuntimeStatuses(
        camera_status=_aggregate_camera_status(camera_statuses),
        model_status="not_started",
        inference_status="not_started",
        camera_statuses=camera_statuses,
        model_statuses={camera_id: "not_started" for camera_id in camera_statuses},
    )


def stop_live_runtime(app: FastAPI) -> None:
    controller = getattr(app.state, "runtime_controller", None)
    if controller is not None:
        controller.shutdown()


def _publish_camera_frames(
    camera_id: str,
    frame_buffer: LatestFrameBuffer,
    renderer: FrameRenderer,
    annotated_frame_store: Any,
    stop_event: threading.Event,
    should_publish: Callable[[str], bool] | None = None,
) -> None:
    last_sequence_id = -1
    while not stop_event.is_set():
        packet = frame_buffer.wait_for_newer(last_sequence_id, timeout=0.5)
        if packet is None:
            continue
        if should_publish is not None and not should_publish(camera_id):
            last_sequence_id = packet.sequence_id
            continue
        annotated_frame_store.publish(
            AnnotatedFrame(
                sequence_id=packet.sequence_id,
                captured_at=packet.captured_at,
                frame=renderer.render(packet.frame, detections=[]),
                source_captured_at=packet.source_captured_at,
            )
        )
        last_sequence_id = packet.sequence_id


def _aggregate_camera_status(statuses: Mapping[str, str]) -> str:
    if not statuses:
        return CameraStatus.NOT_STARTED.value
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
    if not statuses:
        return "not_started"
    values = set(statuses.values())
    if len(values) == 1:
        return next(iter(values))
    if "error" in values:
        return "error"
    if "loading" in values:
        return "loading"
    if "loaded" in values and values.issubset({"loaded", "unassigned"}):
        return "loaded"
    return "partial"
