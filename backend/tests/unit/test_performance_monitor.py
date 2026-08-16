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


def test_performance_monitor_tracks_capture_delay_per_camera() -> None:
    monitor = PerformanceMonitor(window_size=3)
    captured_at = datetime.now(UTC)

    monitor.record_capture(captured_at, capture_to_host_ms=10.0, camera_id="camera_1")
    monitor.record_capture(captured_at, capture_to_host_ms=14.0, camera_id="camera_1")
    monitor.record_capture(captured_at, capture_to_host_ms=30.0, camera_id="camera_2")

    snapshot = monitor.snapshot()
    assert snapshot.latest_capture_to_host_ms_by_camera == {
        "camera_1": 14.0,
        "camera_2": 30.0,
    }
    assert snapshot.average_capture_to_host_ms_by_camera == {
        "camera_1": 12.0,
        "camera_2": 30.0,
    }
    assert snapshot.source_timestamp_frames_by_camera == {
        "camera_1": 2,
        "camera_2": 1,
    }


def test_performance_monitor_tracks_inference_and_total_latency_per_camera() -> None:
    monitor = PerformanceMonitor(window_size=3)

    monitor.record_inference(
        latency_ms=20.0,
        camera_id="camera_2",
        total_latency_ms=120.0,
    )
    monitor.record_inference(
        latency_ms=30.0,
        camera_id="camera_2",
        total_latency_ms=140.0,
    )

    snapshot = monitor.snapshot()
    assert snapshot.latest_inference_ms_by_camera == {"camera_2": 30.0}
    assert snapshot.average_inference_ms_by_camera == {"camera_2": 25.0}
    assert snapshot.latest_total_latency_ms_by_camera == {"camera_2": 140.0}
    assert snapshot.average_total_latency_ms_by_camera == {"camera_2": 130.0}
