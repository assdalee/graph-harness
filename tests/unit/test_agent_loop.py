from typing import Any

import pytest
from pydantic import BaseModel

from graph_harness.agent.agent import GraphAgent
from graph_harness.core.config import Settings
from graph_harness.llm.types import LLMResponse, LLMToolCall
from graph_harness.tools.base import ToolDefinition
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.registry import ToolRegistry
from graph_harness.tools.results import ToolResult


class EchoArgs(BaseModel):
    value: str


async def echo(args: EchoArgs) -> dict[str, Any]:
    return {"value": args.value}


async def invalid_filter(_args: EchoArgs) -> ToolResult:
    return ToolResult.failure("invalid_filter", "Unsupported OData filter property.")


async def permission_denied(_args: EchoArgs) -> ToolResult:
    return ToolResult.failure("permission_denied", "Insufficient privileges.")


class FakeLLM:
    def __init__(self, responses: list[LLMResponse | Exception]) -> None:
        self.responses = responses
        self.calls = 0
        self.seen_messages: list[list[dict[str, Any]]] = []

    async def complete(self, **kwargs: Any) -> LLMResponse:
        self.calls += 1
        self.seen_messages.append(kwargs.get("messages") or [])
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def build_agent(fake_llm: FakeLLM, **settings_kwargs: Any) -> GraphAgent:
    registry = ToolRegistry()
    registry.register(ToolDefinition("echo", "Echo input.", EchoArgs, echo))
    registry.register(ToolDefinition("invalid_filter", "Return invalid filter.", EchoArgs, invalid_filter))
    registry.register(ToolDefinition("permission_denied", "Return permission error.", EchoArgs, permission_denied))
    settings = Settings(**settings_kwargs)
    executor = ToolExecutor(registry, settings)
    return GraphAgent(llm_client=fake_llm, registry=registry, executor=executor, settings=settings)


@pytest.mark.asyncio
async def test_retries_empty_model_response_then_accepts_answer() -> None:
    fake_llm = FakeLLM(
        [
            LLMResponse(content=""),
            LLMResponse(content="Done."),
        ]
    )
    agent = build_agent(fake_llm, agent_empty_response_retries=1)

    response = await agent.run(messages=[{"role": "user", "content": "hello"}])

    assert response.answer == "Done."
    assert response.status == "completed"
    assert response.stop_reason == "final_answer"
    assert "empty response" in response.warnings[0]
    assert "run_started" in [event.event for event in response.trace_events]
    assert "run_completed" in [event.event for event in response.trace_events]


@pytest.mark.asyncio
async def test_repeated_tool_calls_stop_with_partial_fallback() -> None:
    call = LLMToolCall(id="1", name="echo", args={"value": "same"})
    fake_llm = FakeLLM(
        [
            LLMResponse(tool_calls=[call]),
            LLMResponse(tool_calls=[call]),
            LLMResponse(content=""),
        ]
    )
    agent = build_agent(
        fake_llm,
        agent_max_turns=4,
        agent_repeated_tool_call_limit=1,
        agent_empty_response_retries=0,
    )

    response = await agent.run(messages=[{"role": "user", "content": "loop"}])

    assert response.status == "partial"
    assert response.stop_reason == "repeated_tool_calls"
    assert response.tool_calls[0].result.ok is True
    assert any("Skipped repeated tool call" in warning for warning in response.warnings)


@pytest.mark.asyncio
async def test_llm_error_returns_failed_response_after_retries() -> None:
    fake_llm = FakeLLM([RuntimeError("boom"), RuntimeError("boom again")])
    agent = build_agent(fake_llm, agent_llm_retries=1)

    response = await agent.run(messages=[{"role": "user", "content": "hello"}])

    assert response.status == "failed"
    assert response.stop_reason == "llm_error"
    assert "could not complete" in response.answer.lower()
    assert fake_llm.calls == 2


@pytest.mark.asyncio
async def test_retryable_tool_error_adds_recovery_instruction() -> None:
    fake_llm = FakeLLM(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(id="1", name="invalid_filter", args={"value": "bad"})
                ]
            ),
            LLMResponse(content="Recovered with a safer query."),
        ]
    )
    agent = build_agent(fake_llm, agent_recovery_max_attempts=1)

    response = await agent.run(messages=[{"role": "user", "content": "bad filter"}])

    assert response.status == "completed"
    assert response.answer == "Recovered with a safer query."
    assert any("Attempting recovery" in warning for warning in response.warnings)
    assert any("Recovery policy instruction" in message["content"] for message in response.messages)
    assert "recovery_directive" in [event.event for event in response.trace_events]


@pytest.mark.asyncio
async def test_terminal_tool_error_finalizes_without_retrying_tool() -> None:
    fake_llm = FakeLLM(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(id="1", name="permission_denied", args={"value": "x"})
                ]
            ),
            LLMResponse(content="You need additional Microsoft Graph permissions."),
        ]
    )
    agent = build_agent(fake_llm)

    response = await agent.run(messages=[{"role": "user", "content": "secure action"}])

    assert response.status == "completed"
    assert response.stop_reason == "tool_error_permission_denied"
    assert response.answer == "You need additional Microsoft Graph permissions."
    assert fake_llm.calls == 2


@pytest.mark.asyncio
async def test_recovery_exhaustion_finalizes() -> None:
    fake_llm = FakeLLM(
        [
            LLMResponse(
                tool_calls=[
                    LLMToolCall(id="1", name="invalid_filter", args={"value": "bad"})
                ]
            ),
            LLMResponse(content="The filter is unsupported."),
        ]
    )
    agent = build_agent(fake_llm, agent_recovery_max_attempts=0)

    response = await agent.run(messages=[{"role": "user", "content": "bad filter"}])

    assert response.status == "completed"
    assert response.stop_reason == "recovery_exhausted"
    assert response.answer == "The filter is unsupported."


@pytest.mark.asyncio
async def test_agent_compacts_context_for_llm_but_keeps_raw_messages() -> None:
    fake_llm = FakeLLM([LLMResponse(content="Done.")])
    agent = build_agent(fake_llm, agent_context_recent_messages=4)
    messages = [{"role": "user", "content": f"message {index}"} for index in range(12)]

    response = await agent.run(messages=messages)

    assert response.status == "completed"
    assert len(fake_llm.seen_messages[0]) < len(response.messages)
    assert any(event.event == "context_compacted" for event in response.trace_events)
    assert len(response.messages) >= 13  # system + original user messages + assistant answer
