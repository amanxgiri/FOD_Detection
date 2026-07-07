from fastapi import APIRouter

from app.schemas.system import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        ready=True,
        camera="not_started",
        model="not_started",
        inference_worker="not_started",
    )
