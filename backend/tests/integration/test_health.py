from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_responds() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "ready": True,
        "camera": "not_started",
        "model": "not_started",
        "inference_worker": "not_started",
    }


def test_config_endpoint_exposes_safe_runtime_settings() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/config")

    assert response.status_code == 200
    body = response.json()
    assert body["model_runtime"] == "tensorrt"
    assert body["model_device"] == "cuda:0"
    assert "database_url" not in body
