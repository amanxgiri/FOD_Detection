from app.monitoring.system_monitor import (
    inference_status_from_engine,
    websocket_status_from_connection_count,
)


class FakeInferenceEngine:
    def __init__(self, status: str) -> None:
        self.status = status

    def get_status(self) -> str:
        return self.status


def test_inference_status_uses_engine_status() -> None:
    assert inference_status_from_engine(FakeInferenceEngine("error")) == "error"
    assert inference_status_from_engine(None) == "not_started"


def test_websocket_status_reflects_connection_count() -> None:
    assert websocket_status_from_connection_count(0) == "not_connected"
    assert websocket_status_from_connection_count(2) == "connected"
