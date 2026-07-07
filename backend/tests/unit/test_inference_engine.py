import time
from datetime import UTC, datetime

import numpy as np

from app.camera.frame_buffer import LatestFrameBuffer
from app.camera.types import FramePacket
from app.inference.inference_engine import InferenceEngine
from app.inference.annotated_frame_store import LatestAnnotatedFrameStore
from app.inference.postprocessor import PostProcessor
from app.inference.renderer import FrameRenderer
from app.inference.types import RawDetection
from app.detection.temporal_validator import (
    TemporalValidationConfig,
    TemporalValidator,
)
from app.monitoring.performance_monitor import PerformanceMonitor


class FakeModelAdapter:
    def __init__(self) -> None:
        self.calls = 0
        self.raise_next = False

    def load(self) -> None:
        pass

    def warmup(self) -> None:
        pass

    def predict(self, frame: np.ndarray) -> list[RawDetection]:
        self.calls += 1
        if self.raise_next:
            self.raise_next = False
            raise RuntimeError("synthetic model failure")
        return [RawDetection(1, "Bolt", 0.9, 1, 1, 8, 8)]

    def close(self) -> None:
        pass


def make_packet(sequence_id: int) -> FramePacket:
    return FramePacket(
        sequence_id=sequence_id,
        captured_at=datetime.now(UTC),
        frame=np.zeros((10, 10, 3), dtype=np.uint8),
    )


def test_inference_engine_processes_new_frames_and_updates_metrics() -> None:
    buffer = LatestFrameBuffer()
    adapter = FakeModelAdapter()
    monitor = PerformanceMonitor()
    engine = InferenceEngine(
        frame_buffer=buffer,
        model_adapter=adapter,
        postprocessor=PostProcessor(confidence_threshold=0.25),
        performance_monitor=monitor,
        poll_timeout_seconds=0.01,
    )

    engine.start()
    buffer.publish(make_packet(1))
    wait_for(lambda: engine.get_latest_result() is not None)
    engine.stop()

    result = engine.get_latest_result()
    snapshot = monitor.snapshot()
    assert result is not None
    assert result.sequence_id == 1
    assert result.detections[0].class_name == "Bolt"
    assert result.confirmed_detections[0].class_name == "Bolt"
    assert adapter.calls == 1
    assert snapshot.frames_inferred == 1
    assert engine.is_running() is False


def test_inference_engine_counts_skipped_sequence_ids() -> None:
    buffer = LatestFrameBuffer()
    adapter = FakeModelAdapter()
    monitor = PerformanceMonitor()
    engine = InferenceEngine(
        frame_buffer=buffer,
        model_adapter=adapter,
        postprocessor=PostProcessor(),
        performance_monitor=monitor,
        poll_timeout_seconds=0.01,
    )

    engine.start()
    buffer.publish(make_packet(3))
    wait_for(lambda: monitor.snapshot().frames_inferred == 1)
    engine.stop()

    assert monitor.snapshot().frames_skipped == 2


def test_inference_engine_records_error_and_continues() -> None:
    buffer = LatestFrameBuffer()
    adapter = FakeModelAdapter()
    adapter.raise_next = True
    monitor = PerformanceMonitor()
    engine = InferenceEngine(
        frame_buffer=buffer,
        model_adapter=adapter,
        postprocessor=PostProcessor(),
        performance_monitor=monitor,
        poll_timeout_seconds=0.01,
    )

    engine.start()
    buffer.publish(make_packet(1))
    wait_for(lambda: engine.get_last_error() is not None)
    buffer.publish(make_packet(2))
    wait_for(lambda: engine.get_latest_result() is not None)
    engine.stop()

    assert engine.get_latest_result() is not None
    assert monitor.snapshot().frames_inferred == 1
    assert adapter.calls == 2


def test_inference_engine_publishes_annotated_frame() -> None:
    buffer = LatestFrameBuffer()
    store = LatestAnnotatedFrameStore()
    engine = InferenceEngine(
        frame_buffer=buffer,
        model_adapter=FakeModelAdapter(),
        postprocessor=PostProcessor(),
        performance_monitor=PerformanceMonitor(),
        frame_renderer=FrameRenderer(),
        annotated_frame_store=store,
        poll_timeout_seconds=0.01,
    )

    engine.start()
    buffer.publish(make_packet(1))
    annotated = store.wait_for_newer(0, timeout=1.0)
    engine.stop()

    assert annotated is not None
    assert annotated.sequence_id == 1
    assert annotated.frame.any()


def test_inference_engine_uses_temporal_validator_for_confirmations() -> None:
    buffer = LatestFrameBuffer()
    engine = InferenceEngine(
        frame_buffer=buffer,
        model_adapter=FakeModelAdapter(),
        postprocessor=PostProcessor(),
        performance_monitor=PerformanceMonitor(),
        temporal_validator=TemporalValidator(
            TemporalValidationConfig(window_size=3, required_hits=2, match_iou=0.3)
        ),
        poll_timeout_seconds=0.01,
    )

    engine.start()
    buffer.publish(make_packet(1))
    wait_for(lambda: engine.get_latest_result() is not None)
    first_result = engine.get_latest_result()
    buffer.publish(make_packet(2))
    wait_for(
        lambda: engine.get_latest_result() is not None
        and engine.get_latest_result().sequence_id == 2
    )
    second_result = engine.get_latest_result()
    engine.stop()

    assert first_result is not None
    assert first_result.confirmed_detections == []
    assert second_result is not None
    assert second_result.confirmed_detections[0].class_name == "Bolt"


def wait_for(predicate: object, timeout_seconds: float = 1.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition was not met before timeout")
