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
    print("backend smoke check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
