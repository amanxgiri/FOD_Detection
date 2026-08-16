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
    latest_capture_to_host_ms: float | None
    average_capture_to_host_ms: float | None
    source_timestamp_frames: int
    latest_capture_to_host_ms_by_camera: dict[str, float]
    average_capture_to_host_ms_by_camera: dict[str, float]
    source_timestamp_frames_by_camera: dict[str, int]
    frames_captured_by_camera: dict[str, int]
    latest_inference_ms_by_camera: dict[str, float]
    average_inference_ms_by_camera: dict[str, float]
    latest_total_latency_ms_by_camera: dict[str, float]
    average_total_latency_ms_by_camera: dict[str, float]


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
        self._capture_to_host_latencies_ms: deque[float] = deque(maxlen=window_size)
        self._source_timestamp_frames = 0
        self._capture_to_host_latencies_by_camera: dict[str, deque[float]] = {}
        self._source_timestamp_frames_by_camera: dict[str, int] = {}
        self._frames_captured_by_camera: dict[str, int] = {}
        self._window_size = window_size
        self._inference_latencies_by_camera: dict[str, deque[float]] = {}
        self._total_latencies_by_camera: dict[str, deque[float]] = {}

    def record_capture(
        self,
        captured_at: datetime,
        capture_to_host_ms: float | None = None,
        camera_id: str | None = None,
    ) -> None:
        with self._lock:
            self._frames_captured += 1
            self._latest_frame_timestamp = captured_at
            self._capture_times.append(monotonic())
            if camera_id is not None:
                self._frames_captured_by_camera[camera_id] = (
                    self._frames_captured_by_camera.get(camera_id, 0) + 1
                )
            if capture_to_host_ms is not None:
                self._capture_to_host_latencies_ms.append(capture_to_host_ms)
                self._source_timestamp_frames += 1
                if camera_id is not None:
                    samples = self._capture_to_host_latencies_by_camera.setdefault(
                        camera_id,
                        deque(maxlen=self._window_size),
                    )
                    samples.append(capture_to_host_ms)
                    self._source_timestamp_frames_by_camera[camera_id] = (
                        self._source_timestamp_frames_by_camera.get(camera_id, 0) + 1
                    )

    def record_inference(
        self,
        latency_ms: float,
        skipped_frames: int = 0,
        camera_id: str | None = None,
        total_latency_ms: float | None = None,
    ) -> None:
        with self._lock:
            self._frames_inferred += 1
            self._frames_skipped += max(0, skipped_frames)
            self._inference_latencies_ms.append(latency_ms)
            self._inference_times.append(monotonic())
            if camera_id is not None:
                inference_samples = self._inference_latencies_by_camera.setdefault(
                    camera_id,
                    deque(maxlen=self._window_size),
                )
                inference_samples.append(latency_ms)
                if total_latency_ms is not None:
                    total_samples = self._total_latencies_by_camera.setdefault(
                        camera_id,
                        deque(maxlen=self._window_size),
                    )
                    total_samples.append(total_latency_ms)

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
            latest_capture_to_host_ms = (
                self._capture_to_host_latencies_ms[-1]
                if self._capture_to_host_latencies_ms
                else None
            )
            average_capture_to_host_ms = (
                sum(self._capture_to_host_latencies_ms)
                / len(self._capture_to_host_latencies_ms)
                if self._capture_to_host_latencies_ms
                else None
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
                latest_capture_to_host_ms=latest_capture_to_host_ms,
                average_capture_to_host_ms=average_capture_to_host_ms,
                source_timestamp_frames=self._source_timestamp_frames,
                latest_capture_to_host_ms_by_camera={
                    camera_id: samples[-1]
                    for camera_id, samples in self._capture_to_host_latencies_by_camera.items()
                    if samples
                },
                average_capture_to_host_ms_by_camera={
                    camera_id: sum(samples) / len(samples)
                    for camera_id, samples in self._capture_to_host_latencies_by_camera.items()
                    if samples
                },
                source_timestamp_frames_by_camera=dict(
                    self._source_timestamp_frames_by_camera
                ),
                frames_captured_by_camera=dict(self._frames_captured_by_camera),
                latest_inference_ms_by_camera={
                    camera_id: samples[-1]
                    for camera_id, samples in self._inference_latencies_by_camera.items()
                    if samples
                },
                average_inference_ms_by_camera={
                    camera_id: sum(samples) / len(samples)
                    for camera_id, samples in self._inference_latencies_by_camera.items()
                    if samples
                },
                latest_total_latency_ms_by_camera={
                    camera_id: samples[-1]
                    for camera_id, samples in self._total_latencies_by_camera.items()
                    if samples
                },
                average_total_latency_ms_by_camera={
                    camera_id: sum(samples) / len(samples)
                    for camera_id, samples in self._total_latencies_by_camera.items()
                    if samples
                },
            )

    @staticmethod
    def _calculate_fps(samples: deque[float]) -> float:
        if len(samples) < 2:
            return 0.0
        elapsed = samples[-1] - samples[0]
        if elapsed <= 0:
            return 0.0
        return (len(samples) - 1) / elapsed
