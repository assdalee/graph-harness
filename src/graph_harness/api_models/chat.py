"""Pydantic request/response and streaming-event models for the chat HTTP API."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_harness.tools.results import ToolError, ToolResult


MessageRole = Literal["system", "user", "assistant", "tool"]


class ChatMessageIn(BaseModel):
    """A single inbound conversation message in an OpenAI-style chat payload."""

    model_config = ConfigDict(extra="allow")

    role: MessageRole | str = Field(default="user")
    content: str = Field(default="")
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


class ChatInput(BaseModel):
    """Normalized chat input: the message list plus thread and user identifiers."""

    model_config = ConfigDict(extra="allow")

    messages: list[ChatMessageIn] = Field(default_factory=list)
    thread_id: str | None = None
    user_id: str | None = None


class ChatRequest(BaseModel):
    """Top-level chat request accepting either a nested input or top-level fields."""

    model_config = ConfigDict(extra="allow")

    input: ChatInput | None = None
    messages: list[ChatMessageIn] | None = None
    thread_id: str | None = None
    user_id: str | None = None
    tags: dict[str, Any] = Field(default_factory=dict)

    def normalized_input(self) -> ChatInput:
        """Coalesce nested or top-level fields into a single ChatInput."""
        if self.input is not None:
            return self.input
        return ChatInput(
            messages=self.messages or [],
            thread_id=self.thread_id,
            user_id=self.user_id,
        )


class ToolCallRecord(BaseModel):
    """Record of one tool invocation with its arguments and result or error."""

    id: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: ToolResult | None = None
    error: ToolError | None = None
    read_only: bool = True


class AgentTraceEvent(BaseModel):
    """A single observability event emitted during an agent run turn."""

    event: str
    turn: int = 0
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMCallRecord(BaseModel):
    """The exact constructed prompt sent to the model on one agent loop call."""

    turn: int = 0
    phase: str = "turn"
    compacted: bool = False
    tool_count: int = 0
    messages: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Full chat response payload: the answer plus run metadata and trace details."""

    thread_id: str | None = None
    run_id: str | None = None
    answer: str = ""
    status: str = Field(default="completed")
    stop_reason: str = Field(default="final_answer")
    turns: int = Field(default=0)
    data: list[Any] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)


class StreamTraceEvent(BaseModel):
    """Streamed SSE frame carrying an interim agent trace event."""

    event: Literal["trace"]
    data: AgentTraceEvent


class StreamResultEvent(BaseModel):
    """Streamed SSE frame carrying the final chat response."""

    event: Literal["result"]
    data: ChatResponse


class StreamDoneEvent(BaseModel):
    """Streamed SSE frame signaling the stream has ended."""

    event: Literal["done"]


class StreamErrorEvent(BaseModel):
    """Streamed SSE frame reporting an error that aborted the run."""

    event: Literal["error"]
    detail: str
    code: str | None = None
