from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.inference.annotated_frame_store import LatestAnnotatedFrameStore
from app.monitoring.performance_monitor import PerformanceMonitor

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
    yield
    logger.info("application shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="FOD Detection Prototype API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.annotated_frame_store = LatestAnnotatedFrameStore()
    app.state.performance_monitor = PerformanceMonitor()
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
