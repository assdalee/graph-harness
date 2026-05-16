from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from graph_harness.agent.state import AgentRunState
from graph_harness.api_models.chat import ToolCallRecord
from graph_harness.core.config import Settings
from graph_harness.tools.results import ToolErrorCode


RecoveryAction = Literal["continue", "finalize"]


@dataclass(frozen=True)
class RecoveryDirective:
    action: RecoveryAction
    message: str
    stop_reason: str
    warning: str


class ErrorRecoveryPolicy:
    """Harness-level recovery for typed tool errors.

    The policy does not execute tools directly. It decides whether the agent should give the
    model one constrained retry instruction or finalize with a user-facing explanation.
    """

    RETRYABLE_CODES: set[ToolErrorCode] = {
        "invalid_filter",
        "validation_error",
        "not_found",
        "rate_limited",
        "transient_graph_error",
        "upstream_error",
    }
    TERMINAL_CODES: set[ToolErrorCode] = {
        "permission_denied",
        "confirmation_required",
        "ambiguous_identity",
        "unknown_tool",
    }

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def evaluate(
        self,
        records: list[ToolCallRecord],
        state: AgentRunState,
    ) -> RecoveryDirective | None:
        error_records = [record for record in records if record.error]
        if not error_records:
            return None

        terminal = [record for record in error_records if record.error.code in self.TERMINAL_CODES]
        if terminal:
            return self._finalize_directive(terminal[0])

        retryable = [record for record in error_records if record.error.code in self.RETRYABLE_CODES]
        if retryable:
            record = retryable[0]
            key = self._attempt_key(record)
            attempts = state.recovery_attempts.get(key, 0)
            if attempts < self._settings.agent_recovery_max_attempts:
                state.recovery_attempts[key] = attempts + 1
                return self._retry_directive(record, attempts + 1)
            return RecoveryDirective(
                action="finalize",
                message=self._finalize_message(record),
                stop_reason="recovery_exhausted",
                warning=(
                    f"Recovery attempts exhausted for {record.name} "
                    f"({record.error.code})."
                ),
            )

        return self._finalize_directive(error_records[0])

    def _retry_directive(self, record: ToolCallRecord, attempt: int) -> RecoveryDirective:
        assert record.error is not None
        code = record.error.code
        guidance = {
            "invalid_filter": (
                "Retry once using safer structured filter arguments if available. "
                "Avoid repeating the same OData filter. If a broad fetch is safer, use it and "
                "filter in the final answer."
            ),
            "validation_error": (
                "Repair the tool arguments according to the schema. Do not repeat the same "
                "invalid arguments."
            ),
            "not_found": (
                "Resolve the target with resolve_user or resolve_group if this is an identity "
                "lookup. If the target is genuinely absent, explain that."
            ),
            "rate_limited": (
                "Retry only if the request can be made smaller using top/max_pages. Otherwise "
                "finalize with the rate-limit explanation."
            ),
            "transient_graph_error": (
                "Retry once with the same intent. If it fails again, explain the transient "
                "Microsoft Graph failure."
            ),
            "upstream_error": (
                "Retry once only if you can make the request safer or more specific. Otherwise "
                "finalize with the upstream error."
            ),
        }.get(code, "Try one corrected recovery step, then finalize if it still fails.")

        return RecoveryDirective(
            action="continue",
            message=(
                "Recovery policy instruction:\n"
                f"- Tool `{record.name}` failed with `{code}`: {record.error.message}\n"
                f"- Recovery attempt: {attempt}/{self._settings.agent_recovery_max_attempts}\n"
                f"- {guidance}"
            ),
            stop_reason="recovering_tool_error",
            warning=f"Attempting recovery for {record.name} ({code}).",
        )

    def _finalize_directive(self, record: ToolCallRecord) -> RecoveryDirective:
        return RecoveryDirective(
            action="finalize",
            message=self._finalize_message(record),
            stop_reason=f"tool_error_{record.error.code if record.error else 'unknown'}",
            warning=(
                f"Finalizing after non-retryable tool error from {record.name}: "
                f"{record.error.code if record.error else 'unknown'}."
            ),
        )

    def _finalize_message(self, record: ToolCallRecord) -> str:
        if record.error is None:
            return "Explain that tool execution failed and no typed error was available."

        code = record.error.code
        guidance = {
            "permission_denied": "Explain the missing Microsoft Graph permission or admin consent needed.",
            "confirmation_required": "Ask the user for explicit confirmation before attempting the mutation.",
            "ambiguous_identity": "Ask the user to choose the exact user/group from the candidates.",
            "unknown_tool": "Explain that the requested operation is not available in the current tool registry.",
            "invalid_filter": "Explain the unsupported filter and suggest a safer query.",
            "not_found": "Explain that no matching object was found and ask for a more specific identifier.",
            "rate_limited": "Explain that Microsoft Graph rate-limited the request and suggest narrowing the query.",
            "transient_graph_error": "Explain that Microsoft Graph had a transient failure and suggest retrying.",
            "validation_error": "Explain which arguments are invalid and what is required.",
            "upstream_error": "Explain the upstream Microsoft Graph error.",
        }.get(code, "Explain the tool error clearly.")

        return (
            "Recovery policy instruction:\n"
            f"- Tool `{record.name}` failed with `{code}`: {record.error.message}\n"
            f"- {guidance}\n"
            "- Do not call another tool. Provide the user-facing answer now."
        )

    @staticmethod
    def _attempt_key(record: ToolCallRecord) -> str:
        code = record.error.code if record.error else "unknown"
        return f"{record.name}:{code}"

