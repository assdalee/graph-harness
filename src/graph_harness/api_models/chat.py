from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from graph_harness.tools.results import ToolError, ToolResult


MessageRole = Literal["system", "user", "assistant", "tool"]


class ChatMessageIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    role: MessageRole | str = Field(default="user")
    content: str = Field(default="")
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None


class ChatInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    messages: list[ChatMessageIn] = Field(default_factory=list)
    thread_id: str | None = None
    user_id: str | None = None


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    input: ChatInput | None = None
    messages: list[ChatMessageIn] | None = None
    thread_id: str | None = None
    user_id: str | None = None

    def normalized_input(self) -> ChatInput:
        if self.input is not None:
            return self.input
        return ChatInput(
            messages=self.messages or [],
            thread_id=self.thread_id,
            user_id=self.user_id,
        )


class ToolCallRecord(BaseModel):
    id: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    result: ToolResult | None = None
    error: ToolError | None = None
    read_only: bool = True


class AgentTraceEvent(BaseModel):
    event: str
    turn: int = 0
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    thread_id: str | None = None
    answer: str = ""
    status: str = Field(default="completed")
    stop_reason: str = Field(default="final_answer")
    turns: int = Field(default=0)
    data: list[Any] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)


class StreamResultEvent(BaseModel):
    event: Literal["result"]
    data: ChatResponse


class StreamDoneEvent(BaseModel):
    event: Literal["done"]


class StreamErrorEvent(BaseModel):
    event: Literal["error"]
    detail: str
    code: str | None = None
