from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.camera.discovery import MediaMtxDiscoveryService
from app.core.config import get_settings
from app.core.lifecycle import start_live_runtime, stop_live_runtime
from app.core.logging import configure_logging, get_logger
from app.api.websocket.connection_manager import WebSocketConnectionManager
from app.inference.model_catalog import ModelCatalog
from app.inference.tensorrt_export import ensure_tensorrt_engines
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
    generated_engines = ensure_tensorrt_engines(
        source_paths=settings.model_source_paths,
        engine_paths=settings.model_engine_paths,
        device=settings.model_device,
        image_size=settings.model_image_size,
    )
    for engine_path in generated_engines:
        logger.info("automatically created TensorRT engine: %s", engine_path)
    app.state.model_catalog = ModelCatalog(settings.model_catalog_directory)
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
    discovery = MediaMtxDiscoveryService(app)
    app.state.camera_discovery = discovery
    if not hasattr(app.state, "capture_factory"):
        discovery.start()
    try:
        yield
    finally:
        await discovery.stop()
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
    app.state.settings = settings
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
    app.state.annotated_frame_stores = {}
    app.state.annotated_frame_store = None
    app.state.performance_monitor = PerformanceMonitor()
    engine = create_database_engine(settings.database_url)
    init_database(engine)
    app.state.database_engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.evidence_store = EvidenceStore(settings.evidence_directory)
    app.state.websocket_manager = WebSocketConnectionManager()
    app.state.model_catalog = ModelCatalog(settings.model_catalog_directory)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
