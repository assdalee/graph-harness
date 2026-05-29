"""HTTP route exposing the catalog of available tool operations and domains."""

from collections.abc import Callable

from fastapi import APIRouter, Depends

from graph_harness.api_models.operations import OperationsResponse
from graph_harness.app.dependencies import get_operations_service
from graph_harness.services.operations_service import OperationsService


def create_operations_router(auth_dependency: Callable) -> APIRouter:
    """Build the operations router guarded by the given auth dependency."""
    router = APIRouter(prefix="/v1/graph", tags=["graph"], dependencies=[Depends(auth_dependency)])

    @router.get("/operations", response_model=OperationsResponse)
    async def list_operations(
        service: OperationsService = Depends(get_operations_service),
    ) -> OperationsResponse:
        """Return the catalog of operations and domains exposed by the harness."""
        return service.list_operations()

    return router

