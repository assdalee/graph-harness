from fastapi import APIRouter

from graph_harness.api_models.common import HealthResponse


def create_health_router(service_name: str) -> APIRouter:
    router = APIRouter(tags=["system"])

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(status="ok", service=service_name)

    return router

