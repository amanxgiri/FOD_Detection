from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import create_app


def test_system_status_endpoint_returns_measured_defaults() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    body = response.json()
    assert body["backend_status"] == "online"
    assert body["camera_status"] == "not_started"
    assert body["model_status"] == "not_started"
    assert body["inference_status"] == "not_started"
    assert body["latest_frame_age_ms"] is None
    assert body["capture_to_host_ms"] is None
    assert body["average_capture_to_host_ms"] is None
    assert body["source_timestamp_frames"] == 0
    assert body["total_confirmed_detections"] == 0


def test_system_status_reports_latest_frame_age() -> None:
    app = create_app()
    app.state.performance_monitor.record_capture(
        datetime.now(UTC) - timedelta(milliseconds=25)
    )
    client = TestClient(app)

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    assert response.json()["latest_frame_age_ms"] >= 0


def test_system_status_reports_sensor_capture_delay() -> None:
    app = create_app()
    app.state.performance_monitor.record_capture(
        datetime.now(UTC), capture_to_host_ms=37.25
    )
    client = TestClient(app)

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    assert response.json()["capture_to_host_ms"] == 37.25
    assert response.json()["average_capture_to_host_ms"] == 37.25
    assert response.json()["source_timestamp_frames"] == 1
