from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from time import monotonic


@dataclass(frozen=True)
class PerformanceSnapshot:
    capture_fps: float
    inference_fps: float
    last_inference_ms: float
    average_inference_ms: float
    frames_captured: int
    frames_inferred: int
    frames_skipped: int
    confirmed_detection_count: int
    latest_frame_timestamp: datetime | None
    camera_read_failures: int


class PerformanceMonitor:
    def __init__(self, window_size: int = 120) -> None:
        if window_size <= 0:
            raise ValueError("window_size must be positive")
        self._lock = Lock()
        self._capture_times: deque[float] = deque(maxlen=window_size)
        self._inference_times: deque[float] = deque(maxlen=window_size)
        self._inference_latencies_ms: deque[float] = deque(maxlen=window_size)
        self._frames_captured = 0
        self._frames_inferred = 0
        self._frames_skipped = 0
        self._confirmed_detection_count = 0
        self._latest_frame_timestamp: datetime | None = None
        self._camera_read_failures = 0

    def record_capture(self, captured_at: datetime) -> None:
        with self._lock:
            self._frames_captured += 1
            self._latest_frame_timestamp = captured_at
            self._capture_times.append(monotonic())

    def record_inference(self, latency_ms: float, skipped_frames: int = 0) -> None:
        with self._lock:
            self._frames_inferred += 1
            self._frames_skipped += max(0, skipped_frames)
            self._inference_latencies_ms.append(latency_ms)
            self._inference_times.append(monotonic())

    def record_camera_read_failure(self) -> None:
        with self._lock:
            self._camera_read_failures += 1

    def record_confirmed_detection(self) -> None:
        with self._lock:
            self._confirmed_detection_count += 1

    def snapshot(self) -> PerformanceSnapshot:
        with self._lock:
            last_inference_ms = (
                self._inference_latencies_ms[-1]
                if self._inference_latencies_ms
                else 0.0
            )
            average_inference_ms = (
                sum(self._inference_latencies_ms) / len(self._inference_latencies_ms)
                if self._inference_latencies_ms
                else 0.0
            )
            return PerformanceSnapshot(
                capture_fps=self._calculate_fps(self._capture_times),
                inference_fps=self._calculate_fps(self._inference_times),
                last_inference_ms=last_inference_ms,
                average_inference_ms=average_inference_ms,
                frames_captured=self._frames_captured,
                frames_inferred=self._frames_inferred,
                frames_skipped=self._frames_skipped,
                confirmed_detection_count=self._confirmed_detection_count,
                latest_frame_timestamp=self._latest_frame_timestamp,
                camera_read_failures=self._camera_read_failures,
            )

    @staticmethod
    def _calculate_fps(samples: deque[float]) -> float:
        if len(samples) < 2:
            return 0.0
        elapsed = samples[-1] - samples[0]
        if elapsed <= 0:
            return 0.0
        return (len(samples) - 1) / elapsed
