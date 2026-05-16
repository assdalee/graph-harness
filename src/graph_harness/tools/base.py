import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, model_validator


ToolHandler = Callable[[BaseModel], Awaitable[Any] | Any]


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel]
    handler: ToolHandler
    read_only: bool = True
    requires_confirmation: bool = False

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_model.model_json_schema(),
            },
        }

    async def invoke(self, args: dict[str, Any]) -> Any:
        parsed = self.args_model.model_validate(args)
        result = self.handler(parsed)
        if inspect.isawaitable(result):
            return await result
        return result


class ConfirmableArgs(BaseModel):
    confirmed: bool = False
    reason: str | None = Field(
        default=None,
        description="Required when confirmed=true. Explain why this mutation is being performed.",
    )
    target_display: str | None = Field(
        default=None,
        description="Human-readable target being changed, used for audit and confirmation.",
    )

    @model_validator(mode="after")
    def require_audit_reason_when_confirmed(self) -> "ConfirmableArgs":
        if self.confirmed and not (self.reason or "").strip():
            raise ValueError("reason is required when confirmed=true")
        return self
