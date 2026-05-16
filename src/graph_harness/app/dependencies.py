from fastapi import Request

from graph_harness.runs.store import RunStore
from graph_harness.services.chat_service import ChatService
from graph_harness.services.operations_service import OperationsService


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def get_operations_service(request: Request) -> OperationsService:
    return request.app.state.operations_service


def get_run_store(request: Request) -> RunStore:
    return request.app.state.run_store

