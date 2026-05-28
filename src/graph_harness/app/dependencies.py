"""FastAPI dependency providers that resolve services from app state."""

from fastapi import Request

from graph_harness.runs.store import RunStore
from graph_harness.services.chat_service import ChatService
from graph_harness.services.operations_service import OperationsService


def get_chat_service(request: Request) -> ChatService:
    """Resolve the ChatService instance wired into app state."""
    return request.app.state.chat_service


def get_operations_service(request: Request) -> OperationsService:
    """Resolve the OperationsService instance wired into app state."""
    return request.app.state.operations_service


def get_run_store(request: Request) -> RunStore:
    """Resolve the RunStore instance wired into app state."""
    return request.app.state.run_store

