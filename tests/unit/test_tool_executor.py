from typing import Any

import pytest
from pydantic import BaseModel

from graph_harness.core.config import Settings
from graph_harness.llm.types import LLMToolCall
from graph_harness.tools.base import ConfirmableArgs, ToolDefinition
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.registry import ToolRegistry


class EchoArgs(BaseModel):
    value: str


class MutateArgs(ConfirmableArgs):
    value: str


async def echo(args: EchoArgs) -> dict[str, Any]:
    return {"value": args.value}


async def mutate(args: MutateArgs) -> dict[str, Any]:
    return {"mutated": args.value}


def build_executor() -> ToolExecutor:
    registry = ToolRegistry()
    registry.register(ToolDefinition("echo", "Echo input.", EchoArgs, echo))
    registry.register(
        ToolDefinition(
            "mutate",
            "Mutate something.",
            MutateArgs,
            mutate,
            read_only=False,
            requires_confirmation=True,
        )
    )
    return ToolExecutor(registry, Settings())


@pytest.mark.asyncio
async def test_executes_valid_read_tool() -> None:
    executor = build_executor()
    records = await executor.execute_calls([LLMToolCall(id="1", name="echo", args={"value": "ok"})])

    assert records[0].error is None
    assert records[0].result.ok is True
    assert records[0].result.data == {"value": "ok"}
    assert records[0].result.summary == "Returned object with keys: value."


@pytest.mark.asyncio
async def test_blocks_unconfirmed_mutation() -> None:
    executor = build_executor()
    records = await executor.execute_calls([LLMToolCall(id="1", name="mutate", args={"value": "x"})])

    assert records[0].result.ok is False
    assert records[0].error.code == "confirmation_required"
    assert "requires confirmed=true" in records[0].error.message


@pytest.mark.asyncio
async def test_allows_confirmed_mutation() -> None:
    executor = build_executor()
    records = await executor.execute_calls(
        [
            LLMToolCall(
                id="1",
                name="mutate",
                args={"value": "x", "confirmed": True, "reason": "unit test"},
            )
        ]
    )

    assert records[0].error is None
    assert records[0].result.ok is True
    assert records[0].result.data == {"mutated": "x"}


@pytest.mark.asyncio
async def test_confirmed_mutation_requires_reason() -> None:
    executor = build_executor()
    records = await executor.execute_calls(
        [LLMToolCall(id="1", name="mutate", args={"value": "x", "confirmed": True})]
    )

    assert records[0].result.ok is False
    assert records[0].error.code == "validation_error"
