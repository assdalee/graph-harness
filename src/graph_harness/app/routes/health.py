"""HTTP route exposing a liveness health check for the service."""

from fastapi import APIRouter

from graph_harness.api_models.common import HealthResponse


def create_health_router(service_name: str) -> APIRouter:
    """Build the unauthenticated health-check router for the named service."""
    router = APIRouter(tags=["system"])

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Report that the service is up."""
        return HealthResponse(status="ok", service=service_name)

    return router

