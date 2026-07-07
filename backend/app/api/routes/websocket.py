from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.websocket.connection_manager import WebSocketConnectionManager

router = APIRouter(prefix="/ws")


@router.websocket("/events")
async def websocket_events(websocket: WebSocket) -> None:
    manager = get_connection_manager(websocket)
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def get_connection_manager(websocket: WebSocket) -> WebSocketConnectionManager:
    manager = getattr(websocket.app.state, "websocket_manager", None)
    if manager is None:
        manager = WebSocketConnectionManager()
        websocket.app.state.websocket_manager = manager
    return manager
