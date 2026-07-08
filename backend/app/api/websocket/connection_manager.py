from __future__ import annotations

from fastapi import WebSocket

from app.api.websocket.events import EventEnvelope, SystemWarningData, make_event


class WebSocketConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, event: EventEnvelope) -> None:
        disconnected: list[WebSocket] = []
        payload = event.model_dump(mode="json")
        for websocket in list(self._connections):
            try:
                await websocket.send_json(payload)
            except RuntimeError:
                disconnected.append(websocket)
        for websocket in disconnected:
            self.disconnect(websocket)

    async def broadcast_warning(self, message: str) -> None:
        await self.broadcast(make_event("system.warning", SystemWarningData(message=message)))
