from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.lifecycle import start_live_runtime, stop_live_runtime
from app.core.logging import configure_logging, get_logger
from app.api.websocket.connection_manager import WebSocketConnectionManager
from app.inference.annotated_frame_store import LatestAnnotatedFrameStore
from app.monitoring.performance_monitor import PerformanceMonitor
from app.storage import (
    EvidenceStore,
    create_database_engine,
    create_session_factory,
    init_database,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("application startup")
    app.state.settings = settings
    if not hasattr(app.state, "annotated_frame_store"):
        app.state.annotated_frame_store = LatestAnnotatedFrameStore()
    if not hasattr(app.state, "performance_monitor"):
        app.state.performance_monitor = PerformanceMonitor()
    if not hasattr(app.state, "session_factory"):
        engine = create_database_engine(settings.database_url)
        init_database(engine)
        app.state.database_engine = engine
        app.state.session_factory = create_session_factory(engine)
    if not hasattr(app.state, "evidence_store"):
        app.state.evidence_store = EvidenceStore(settings.evidence_directory)
    if not hasattr(app.state, "websocket_manager"):
        app.state.websocket_manager = WebSocketConnectionManager()
    start_live_runtime(app)
    try:
        yield
    finally:
        stop_live_runtime(app)
        logger.info("application shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="FOD Detection Prototype API",
        version="0.1.0",
        lifespan=lifespan,
    )
    frontend_origins = list(
        {
            settings.frontend_origin,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        }
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=frontend_origins,
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):51[0-9]{2}$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.annotated_frame_store = LatestAnnotatedFrameStore()
    app.state.performance_monitor = PerformanceMonitor()
    engine = create_database_engine(settings.database_url)
    init_database(engine)
    app.state.database_engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.evidence_store = EvidenceStore(settings.evidence_directory)
    app.state.websocket_manager = WebSocketConnectionManager()
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
