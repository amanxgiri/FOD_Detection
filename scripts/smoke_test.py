import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app


def main() -> int:
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    if response.status_code != 200:
        print(f"health check failed: {response.status_code}")
        return 1
    status_response = client.get("/api/v1/system/status")
    if status_response.status_code != 200:
        print(f"system status check failed: {status_response.status_code}")
        return 1
    detections_response = client.get("/api/v1/detections")
    if detections_response.status_code != 200:
        print(f"detections check failed: {detections_response.status_code}")
        return 1
    with client.websocket_connect("/api/v1/ws/events") as websocket:
        websocket.send_text("smoke")
    stream_response = client.get("/api/v1/stream?frame_limit=1")
    if stream_response.status_code != 200:
        print(f"stream check failed: {stream_response.status_code}")
        return 1
    if b"Content-Type: image/jpeg" not in stream_response.content:
        print("stream check failed: missing JPEG multipart payload")
        return 1
    print("backend smoke check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
