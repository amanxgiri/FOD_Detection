from fastapi.testclient import TestClient

from app.api.websocket.events import make_event
from app.main import create_app


def test_websocket_connection_receives_broadcast_event() -> None:
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/events") as websocket:
        websocket.portal.call(
            app.state.websocket_manager.broadcast,
            make_event("system.warning", {"message": "test warning"}),
        )
        payload = websocket.receive_json()

    assert payload["type"] == "system.warning"
    assert payload["data"] == {"message": "test warning"}


def test_websocket_disconnect_cleans_connection() -> None:
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/events"):
        assert app.state.websocket_manager.connection_count == 1

    assert app.state.websocket_manager.connection_count == 0


def test_websocket_receives_system_warning_helper_event() -> None:
    app = create_app()
    client = TestClient(app)

    with client.websocket_connect("/api/v1/ws/events") as websocket:
        websocket.portal.call(
            app.state.websocket_manager.broadcast_warning,
            "runtime warning",
        )
        payload = websocket.receive_json()

    assert payload["type"] == "system.warning"
    assert payload["data"] == {"message": "runtime warning"}
