from fastapi import APIRouter

from app.api.routes import config, detections, health, stream, system

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(config.router, tags=["config"])
api_router.include_router(stream.router, tags=["stream"])
api_router.include_router(system.router, tags=["system"])
api_router.include_router(detections.router, tags=["detections"])
