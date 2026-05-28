"""Hold the mutable per-run state threaded through a single agent invocation."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from graph_harness.api_models.chat import AgentTraceEvent, LLMCallRecord, ToolCallRecord


class AgentRunState(BaseModel):
    """Accumulate messages, tool results, trace events, and stop bookkeeping for one run."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    messages: list[dict[str, Any]]
    turn: int = 0
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    data: list[Any] = Field(default_factory=list)
    stop_reason: str = "not_started"
    status: str = "running"
    warnings: list[str] = Field(default_factory=list)
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)
    empty_response_count: int = 0
    recovery_attempts: dict[str, int] = Field(default_factory=dict)
    on_event: Callable[[AgentTraceEvent], None] | None = Field(
        default=None, exclude=True, repr=False
    )
