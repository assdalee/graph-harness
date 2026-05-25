import pytest

from graph_harness.core.config import Settings
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.types import LLMToolCall
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import GraphToolFactory


def _executor() -> ToolExecutor:
    registry = GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()
    return ToolExecutor(registry, Settings(graph_backend="mock", llm_backend="fake"))


@pytest.mark.asyncio
async def test_generic_mutation_requires_confirmation_with_typed_code() -> None:
    executor = _executor()
    record = await executor.execute_call(
        LLMToolCall(
            id="c1",
            name="graph_operation",
            args={"operation_name": "delete_oauth_permission_grant", "path_params": {"grant_id": "g1"}},
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_generic_unknown_operation_is_validation_error() -> None:
    executor = _executor()
    record = await executor.execute_call(
        LLMToolCall(id="c2", name="graph_operation", args={"operation_name": "does_not_exist"})
    )
    assert record.error is not None
    assert record.error.code == "validation_error"


@pytest.mark.asyncio
async def test_generic_missing_path_param_is_validation_error() -> None:
    executor = _executor()
    record = await executor.execute_call(
        LLMToolCall(
            id="c3",
            name="graph_operation",
            args={
                "operation_name": "delete_oauth_permission_grant",
                "confirmed": True,
                "reason": "cleanup",
                "path_params": {},
            },
        )
    )
    assert record.error is not None
    assert record.error.code == "validation_error"


@pytest.mark.asyncio
async def test_generic_read_operation_runs_without_confirmation() -> None:
    executor = _executor()
    record = await executor.execute_call(
        LLMToolCall(id="c4", name="graph_operation", args={"operation_name": "list_users"})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok
