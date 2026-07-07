from fastapi import APIRouter

from app.api.routes import config, health, stream

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(config.router, tags=["config"])
api_router.include_router(stream.router, tags=["stream"])
