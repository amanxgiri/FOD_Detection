from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.camera.frame_buffer import LatestFrameBuffer
from app.detection.types import Detection
from app.detection.temporal_validator import TemporalValidator
from app.inference.annotated_frame_store import AnnotatedFrame, LatestAnnotatedFrameStore
from app.inference.model_adapter import ModelAdapter
from app.inference.postprocessor import PostProcessor
from app.inference.renderer import FrameRenderer
from app.monitoring.performance_monitor import PerformanceMonitor


@dataclass(frozen=True)
class CameraInferenceResult:
    camera_id: str
    sequence_id: int
    detections: list[Detection]
    confirmed_detections: list[Detection]
    inference_ms: float


class RoundRobinInferenceEngine:
    """Serialize three camera/model lanes in a fixed repeating order."""

    def __init__(
        self,
        frame_buffers: dict[str, LatestFrameBuffer],
        model_adapters: dict[str, ModelAdapter],
        annotated_frame_stores: dict[str, LatestAnnotatedFrameStore],
        postprocessor: PostProcessor,
        performance_monitor: PerformanceMonitor,
        temporal_validators: dict[str, TemporalValidator],
        frame_renderer: FrameRenderer | None = None,
        idle_backoff_seconds: float = 0.001,
    ) -> None:
        camera_ids = tuple(frame_buffers)
        if len(camera_ids) != 3:
            raise ValueError("round-robin inference requires exactly three cameras")
        if set(model_adapters) != set(camera_ids):
            raise ValueError("every camera must have exactly one model adapter")
        if set(annotated_frame_stores) != set(camera_ids):
            raise ValueError("every camera must have an annotated frame store")
        if set(temporal_validators) != set(camera_ids):
            raise ValueError("every camera must have an independent temporal validator")

        self._camera_ids = camera_ids
        self._frame_buffers = frame_buffers
        self._model_adapters = model_adapters
        self._annotated_frame_stores = annotated_frame_stores
        self._postprocessor = postprocessor
        self._performance_monitor = performance_monitor
        self._temporal_validators = temporal_validators
        self._frame_renderer = frame_renderer or FrameRenderer()
        self._idle_backoff_seconds = max(0.0, idle_backoff_seconds)

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_sequence_ids = {camera_id: 0 for camera_id in camera_ids}
        self._latest_results: dict[str, CameraInferenceResult] = {}
        self._last_error: str | None = None
        self._active_camera_id: str | None = None
        self._slot_count = 0
        self._missed_slots = 0

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._scheduler_loop,
                name="round-robin-inference",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5)
        with self._lock:
            self._thread = None
            self._active_camera_id = None

    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive() and not self._stop_event.is_set()

    def get_status(self) -> str:
        if self.is_running():
            return "error" if self.get_last_error() else "running"
        return "stopped"

    def get_last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    def get_latest_result(self, camera_id: str) -> CameraInferenceResult | None:
        with self._lock:
            return self._latest_results.get(camera_id)

    @property
    def active_camera_id(self) -> str | None:
        with self._lock:
            return self._active_camera_id

    @property
    def slot_count(self) -> int:
        with self._lock:
            return self._slot_count

    @property
    def missed_slots(self) -> int:
        with self._lock:
            return self._missed_slots

    def _scheduler_loop(self) -> None:
        while not self._stop_event.is_set():
            inferred_in_cycle = False
            for camera_id in self._camera_ids:
                if self._stop_event.is_set():
                    break
                inferred_in_cycle = self._run_slot(camera_id) or inferred_in_cycle
            if not inferred_in_cycle:
                self._stop_event.wait(self._idle_backoff_seconds)

    def _run_slot(self, camera_id: str) -> bool:
        # A turn is a non-blocking snapshot, never a dequeue operation. Frames
        # overwritten before this instant are deliberately skipped forever.
        packet = self._frame_buffers[camera_id].get_latest()
        with self._lock:
            self._slot_count += 1
        if (
            packet is None
            or packet.sequence_id <= self._last_sequence_ids[camera_id]
        ):
            with self._lock:
                self._missed_slots += 1
            return False

        skipped_frames = max(
            0,
            packet.sequence_id - self._last_sequence_ids[camera_id] - 1,
        )
        self._last_sequence_ids[camera_id] = packet.sequence_id
        try:
            if packet.frame.size == 0 or packet.frame.ndim < 2:
                raise ValueError(f"invalid frame from {camera_id}")
            with self._lock:
                self._active_camera_id = camera_id
            started = time.perf_counter()
            raw_detections = self._model_adapters[camera_id].predict(packet.frame)
            inference_ms = (time.perf_counter() - started) * 1000
            frame_height, frame_width = packet.frame.shape[:2]
            detections = self._postprocessor.process(
                raw_detections,
                frame_width=frame_width,
                frame_height=frame_height,
            )
            confirmed = self._temporal_validators[camera_id].process(
                detections,
                sequence_id=packet.sequence_id,
            )
            annotated = self._frame_renderer.render(packet.frame, detections)
            self._annotated_frame_stores[camera_id].publish(
                AnnotatedFrame(
                    sequence_id=packet.sequence_id,
                    captured_at=packet.captured_at,
                    frame=annotated,
                    source_captured_at=packet.source_captured_at,
                )
            )
            result = CameraInferenceResult(
                camera_id=camera_id,
                sequence_id=packet.sequence_id,
                detections=detections,
                confirmed_detections=confirmed,
                inference_ms=inference_ms,
            )
            with self._lock:
                self._latest_results[camera_id] = result
                self._last_error = None
            self._performance_monitor.record_inference(
                latency_ms=inference_ms,
                skipped_frames=skipped_frames,
                camera_id=camera_id,
                total_latency_ms=(
                    packet.capture_to_host_ms + inference_ms
                    if packet.capture_to_host_ms is not None
                    else None
                ),
            )
        except Exception as exc:
            with self._lock:
                self._last_error = f"{camera_id}: {exc}"
        finally:
            with self._lock:
                self._active_camera_id = None
        return True
