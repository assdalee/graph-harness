"""Provider-agnostic LLM response and tool-call models used across the app."""

from typing import Any

from pydantic import BaseModel, Field


class LLMToolCall(BaseModel):
    """A single tool call requested by the model, with parsed arguments."""

    id: str
    name: str
    args: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Normalized model completion holding final content and any tool calls."""

    content: str = ""
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    raw: Any = None

