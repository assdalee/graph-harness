import asyncio
from typing import Any

from pydantic import ValidationError

from graph_harness.api_models.chat import ToolCallRecord
from graph_harness.core.config import Settings
from graph_harness.llm.types import LLMToolCall
from graph_harness.tools.registry import ToolRegistry
from graph_harness.tools.results import ToolResult


class ToolExecutor:
    """Validates and executes model-requested tool calls."""

    def __init__(self, registry: ToolRegistry, settings: Settings) -> None:
        self._registry = registry
        self._settings = settings

    async def execute_calls(self, calls: list[LLMToolCall]) -> list[ToolCallRecord]:
        limited = calls[: self._settings.agent_max_tool_calls]
        if (
            self._settings.agent_parallel_reads
            and len(limited) > 1
            and all(self._is_read_only(call.name) for call in limited)
        ):
            return await asyncio.gather(*(self.execute_call(call) for call in limited))
        records: list[ToolCallRecord] = []
        for call in limited:
            records.append(await self.execute_call(call))
        return records

    async def execute_call(self, call: LLMToolCall) -> ToolCallRecord:
        tool = self._registry.get(call.name)
        if tool is None:
            result = ToolResult.failure("unknown_tool", f"Unknown tool '{call.name}'.")
            return ToolCallRecord(
                id=call.id,
                name=call.name,
                args=call.args,
                result=result,
                error=result.error,
                read_only=False,
            )

        if (
            self._settings.agent_require_mutation_confirmation
            and tool.requires_confirmation
            and not bool(call.args.get("confirmed"))
        ):
            result = ToolResult.failure(
                "confirmation_required",
                (
                    "This operation mutates Microsoft Graph data and requires confirmed=true "
                    "before execution."
                ),
            )
            return ToolCallRecord(
                id=call.id,
                name=call.name,
                args=call.args,
                result=result,
                error=result.error,
                read_only=tool.read_only,
            )

        try:
            result = ToolResult.from_payload(await tool.invoke(call.args))
            return ToolCallRecord(
                id=call.id,
                name=call.name,
                args=call.args,
                result=result,
                error=result.error,
                read_only=tool.read_only,
            )
        except ValidationError as exc:
            result = ToolResult.failure(
                "validation_error",
                "Invalid tool arguments.",
                details={"errors": exc.errors()},
            )
            return ToolCallRecord(
                id=call.id,
                name=call.name,
                args=call.args,
                result=result,
                error=result.error,
                read_only=tool.read_only,
            )
        except Exception as exc:
            result = ToolResult.failure("upstream_error", str(exc))
            return ToolCallRecord(
                id=call.id,
                name=call.name,
                args=call.args,
                result=result,
                error=result.error,
                read_only=tool.read_only,
            )

    def _is_read_only(self, name: str) -> bool:
        tool = self._registry.get(name)
        return bool(tool and tool.read_only)


def extract_data(records: list[ToolCallRecord]) -> list[Any]:
    data: list[Any] = []
    for record in records:
        if record.error:
            continue
        payload = record.result.data if record.result else None
        if isinstance(payload, dict) and isinstance(payload.get("value"), list):
            data.extend(payload["value"])
        elif isinstance(payload, list):
            data.extend(payload)
        elif payload is not None:
            data.append(payload)
    return data
