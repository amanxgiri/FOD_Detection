from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.camera.types import CameraStatus
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
    assert body["capture_to_host_ms_by_camera"] == {}
    assert body["average_capture_to_host_ms_by_camera"] == {}
    assert body["source_timestamp_frames_by_camera"] == {}
    assert body["inference_ms_by_camera"] == {}
    assert body["total_latency_ms_by_camera"] == {}
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
    app.state.camera_managers = {"raspberrypi9": OnlineCamera()}
    app.state.performance_monitor.record_capture(
        datetime.now(UTC), capture_to_host_ms=37.25, camera_id="raspberrypi9"
    )
    client = TestClient(app)

    response = client.get("/api/v1/system/status")

    assert response.status_code == 200
    assert response.json()["capture_to_host_ms"] == 37.25
    assert response.json()["average_capture_to_host_ms"] == 37.25
    assert response.json()["source_timestamp_frames"] == 1
    assert response.json()["capture_to_host_ms_by_camera"]["raspberrypi9"] == 37.25
    assert response.json()["average_capture_to_host_ms_by_camera"]["raspberrypi9"] == 37.25
    assert response.json()["source_timestamp_frames_by_camera"]["raspberrypi9"] == 1
    assert response.json()["total_latency_ms_by_camera"]["raspberrypi9"] == 37.25
    assert response.json()["average_total_latency_ms_by_camera"]["raspberrypi9"] == 37.25


def test_system_status_total_matches_displayed_camera_and_inference_values() -> None:
    app = create_app()
    app.state.camera_managers = {"raspberrypi9": OnlineCamera()}
    app.state.performance_monitor.record_capture(
        datetime.now(UTC), capture_to_host_ms=265.5, camera_id="raspberrypi9"
    )
    app.state.performance_monitor.record_inference(
        2.4, camera_id="raspberrypi9", total_latency_ms=280.0
    )
    app.state.runtime_controller = RunningInferenceRuntime()
    client = TestClient(app)

    body = client.get("/api/v1/system/status").json()

    assert body["capture_to_host_ms_by_camera"]["raspberrypi9"] == 265.5
    assert body["inference_ms_by_camera"]["raspberrypi9"] == 2.4
    assert body["total_latency_ms_by_camera"]["raspberrypi9"] == 267.9


class OnlineCamera:
    def get_status(self) -> CameraStatus:
        return CameraStatus.ONLINE


class RunningInferenceRuntime:
    def get_statuses(self):
        from app.core.lifecycle import RuntimeStatuses

        return RuntimeStatuses(
            camera_status="online",
            model_status="loaded",
            inference_status="running",
            camera_statuses={"raspberrypi9": "online"},
            model_statuses={"raspberrypi9": "loaded"},
        )
