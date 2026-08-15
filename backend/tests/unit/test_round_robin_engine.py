from datetime import UTC, datetime
import threading
import time

import numpy as np

from app.camera.frame_buffer import LatestFrameBuffer
from app.camera.types import FramePacket
from app.detection.temporal_validator import TemporalValidationConfig, TemporalValidator
from app.inference.annotated_frame_store import LatestAnnotatedFrameStore
from app.inference.postprocessor import PostProcessor
from app.inference.round_robin_engine import ParallelInferenceEngine, RoundRobinInferenceEngine
from app.monitoring.performance_monitor import PerformanceMonitor


class RecordingAdapter:
    def __init__(self, camera_id: str, calls: list[str], execution_lock: threading.Lock) -> None:
        self.camera_id = camera_id
        self.calls = calls
        self.execution_lock = execution_lock

    def load(self) -> None:
        pass

    def warmup(self) -> None:
        pass

    def predict(self, frame: np.ndarray) -> list:
        assert self.execution_lock.acquire(blocking=False), "model calls overlapped"
        try:
            self.calls.append(self.camera_id)
            time.sleep(0.002)
            return []
        finally:
            self.execution_lock.release()

    def close(self) -> None:
        pass


def test_round_robin_engine_serializes_three_camera_models() -> None:
    camera_ids = ("camera_1", "camera_2", "camera_3")
    buffers = {camera_id: LatestFrameBuffer() for camera_id in camera_ids}
    stores = {camera_id: LatestAnnotatedFrameStore() for camera_id in camera_ids}
    calls: list[str] = []
    execution_lock = threading.Lock()
    adapters = {
        camera_id: RecordingAdapter(camera_id, calls, execution_lock)
        for camera_id in camera_ids
    }
    validators = {
        camera_id: TemporalValidator(TemporalValidationConfig(enabled=False))
        for camera_id in camera_ids
    }
    engine = RoundRobinInferenceEngine(
        frame_buffers=buffers,
        model_adapters=adapters,
        annotated_frame_stores=stores,
        postprocessor=PostProcessor(confidence_threshold=0.01),
        performance_monitor=PerformanceMonitor(),
        temporal_validators=validators,
    )

    for sequence_id in (1, 2):
        for camera_id in camera_ids:
            buffers[camera_id].publish(
                FramePacket(
                    sequence_id=sequence_id,
                    captured_at=datetime.now(UTC),
                    frame=np.zeros((12, 16, 3), dtype=np.uint8),
                    camera_id=camera_id,
                )
            )
        if sequence_id == 1:
            engine.start()
            wait_for(lambda: len(calls) >= 3)

    wait_for(lambda: len(calls) >= 6)
    engine.stop()

    assert calls[:6] == [
        "camera_1",
        "camera_2",
        "camera_3",
        "camera_1",
        "camera_2",
        "camera_3",
    ]
    assert all(stores[camera_id].get_latest() is not None for camera_id in camera_ids)


def test_round_robin_skips_empty_turns_and_snapshots_only_latest_frame() -> None:
    camera_ids = ("camera_1", "camera_2", "camera_3")
    buffers = {camera_id: LatestFrameBuffer() for camera_id in camera_ids}
    stores = {camera_id: LatestAnnotatedFrameStore() for camera_id in camera_ids}
    calls: list[str] = []
    execution_lock = threading.Lock()
    adapters = {
        camera_id: RecordingAdapter(camera_id, calls, execution_lock)
        for camera_id in camera_ids
    }
    validators = {
        camera_id: TemporalValidator(TemporalValidationConfig(enabled=False))
        for camera_id in camera_ids
    }
    engine = RoundRobinInferenceEngine(
        frame_buffers=buffers,
        model_adapters=adapters,
        annotated_frame_stores=stores,
        postprocessor=PostProcessor(confidence_threshold=0.01),
        performance_monitor=PerformanceMonitor(),
        temporal_validators=validators,
    )
    for sequence_id in (1, 4, 9):
        buffers["camera_2"].publish(
            FramePacket(
                sequence_id=sequence_id,
                captured_at=datetime.now(UTC),
                frame=np.zeros((12, 16, 3), dtype=np.uint8),
                camera_id="camera_2",
            )
        )

    started = time.perf_counter()
    engine.start()
    wait_for(lambda: engine.get_latest_result("camera_2") is not None)
    elapsed = time.perf_counter() - started
    engine.stop()

    result = engine.get_latest_result("camera_2")
    assert result is not None
    assert result.sequence_id == 9
    assert calls == ["camera_2"]
    assert elapsed < 0.1


def test_parallel_engine_runs_three_camera_workers_concurrently() -> None:
    camera_ids = ("camera_1", "camera_2", "camera_3")
    buffers = {camera_id: LatestFrameBuffer() for camera_id in camera_ids}
    stores = {camera_id: LatestAnnotatedFrameStore() for camera_id in camera_ids}
    calls: list[str] = []
    calls_lock = threading.Lock()
    barrier = threading.Barrier(len(camera_ids))

    class ParallelProbeAdapter:
        def __init__(self, camera_id: str) -> None:
            self.camera_id = camera_id

        def load(self) -> None:
            pass

        def warmup(self) -> None:
            pass

        def predict(self, frame: np.ndarray) -> list:
            barrier.wait(timeout=1.0)
            with calls_lock:
                calls.append(self.camera_id)
            time.sleep(0.05)
            return []

        def close(self) -> None:
            pass

    adapters = {camera_id: ParallelProbeAdapter(camera_id) for camera_id in camera_ids}
    validators = {
        camera_id: TemporalValidator(TemporalValidationConfig(enabled=False))
        for camera_id in camera_ids
    }
    engine = ParallelInferenceEngine(
        frame_buffers=buffers,
        model_adapters=adapters,
        annotated_frame_stores=stores,
        postprocessor=PostProcessor(confidence_threshold=0.01),
        performance_monitor=PerformanceMonitor(),
        temporal_validators=validators,
    )

    for camera_id in camera_ids:
        buffers[camera_id].publish(
            FramePacket(
                sequence_id=1,
                captured_at=datetime.now(UTC),
                frame=np.zeros((12, 16, 3), dtype=np.uint8),
                camera_id=camera_id,
            )
        )

    engine.start()
    wait_for(lambda: len(calls) >= 3, timeout_seconds=1.5)
    engine.stop()

    assert sorted(calls) == sorted(camera_ids)
    assert len(calls) == 3


def wait_for(predicate, timeout_seconds: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.005)
    raise AssertionError("condition was not met")
