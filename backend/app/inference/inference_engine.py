from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from app.camera.frame_buffer import LatestFrameBuffer
from app.camera.types import FramePacket
from app.detection.types import Detection
from app.inference.model_adapter import ModelAdapter
from app.inference.postprocessor import PostProcessor
from app.monitoring.performance_monitor import PerformanceMonitor


@dataclass(frozen=True)
class InferenceResult:
    sequence_id: int
    detections: list[Detection]
    inference_ms: float


class InferenceEngine:
    def __init__(
        self,
        frame_buffer: LatestFrameBuffer,
        model_adapter: ModelAdapter,
        postprocessor: PostProcessor,
        performance_monitor: PerformanceMonitor,
        poll_timeout_seconds: float = 0.2,
    ) -> None:
        self._frame_buffer = frame_buffer
        self._model_adapter = model_adapter
        self._postprocessor = postprocessor
        self._performance_monitor = performance_monitor
        self._poll_timeout_seconds = poll_timeout_seconds

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_sequence_id = 0
        self._latest_result: InferenceResult | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._inference_loop,
                name="inference-worker",
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

    def is_running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive() and not self._stop_event.is_set()

    def get_latest_result(self) -> InferenceResult | None:
        with self._lock:
            return self._latest_result

    def get_last_error(self) -> str | None:
        with self._lock:
            return self._last_error

    def _inference_loop(self) -> None:
        while not self._stop_event.is_set():
            packet = self._frame_buffer.wait_for_newer(
                self._last_sequence_id,
                timeout=self._poll_timeout_seconds,
            )
            if packet is None:
                continue
            self._process_packet(packet)

    def _process_packet(self, packet: FramePacket) -> None:
        skipped_frames = max(0, packet.sequence_id - self._last_sequence_id - 1)
        self._last_sequence_id = packet.sequence_id
        try:
            frame_height, frame_width = packet.frame.shape[:2]
            started = time.perf_counter()
            raw_detections = self._model_adapter.predict(packet.frame)
            inference_ms = (time.perf_counter() - started) * 1000
            detections = self._postprocessor.process(
                raw_detections,
                frame_width=frame_width,
                frame_height=frame_height,
            )
            result = InferenceResult(
                sequence_id=packet.sequence_id,
                detections=detections,
                inference_ms=inference_ms,
            )
            with self._lock:
                self._latest_result = result
                self._last_error = None
            self._performance_monitor.record_inference(
                latency_ms=inference_ms,
                skipped_frames=skipped_frames,
            )
        except Exception as exc:  # Worker must remain alive for later frames.
            with self._lock:
                self._last_error = str(exc)
