from datetime import UTC, datetime

from app.monitoring.performance_monitor import PerformanceMonitor


def test_performance_monitor_records_runtime_metrics() -> None:
    monitor = PerformanceMonitor(window_size=3)
    captured_at = datetime.now(UTC)

    monitor.record_capture(captured_at)
    monitor.record_inference(latency_ms=10.0, skipped_frames=2)
    monitor.record_inference(latency_ms=20.0, skipped_frames=0)
    monitor.record_camera_read_failure()
    monitor.record_confirmed_detection()

    snapshot = monitor.snapshot()

    assert snapshot.frames_captured == 1
    assert snapshot.frames_inferred == 2
    assert snapshot.frames_skipped == 2
    assert snapshot.last_inference_ms == 20.0
    assert snapshot.average_inference_ms == 15.0
    assert snapshot.latest_frame_timestamp == captured_at
    assert snapshot.camera_read_failures == 1
    assert snapshot.confirmed_detection_count == 1
