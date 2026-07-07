from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    ready: bool
    camera: str
    model: str
    inference_worker: str
