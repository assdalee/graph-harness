from __future__ import annotations

from dataclasses import dataclass

from graph_harness.api_models.chat import ToolCallRecord
from graph_harness.core.config import Settings


@dataclass(frozen=True)
class ClarificationDecision:
    answer: str
    stop_reason: str
    warning: str


class ClarificationPolicy:
    """Detect cases where asking the user is safer than retrying or finalizing."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def evaluate(self, records: list[ToolCallRecord]) -> ClarificationDecision | None:
        if not self._settings.agent_enable_clarification_policy:
            return None

        for record in records:
            if not record.error:
                continue
            if record.error.code == "confirmation_required":
                return ClarificationDecision(
                    answer=(
                        "I need explicit confirmation before making that Microsoft Graph change. "
                        "Please confirm the exact action, target, and reason."
                    ),
                    stop_reason="clarification_confirmation_required",
                    warning=f"Clarification required before mutation tool {record.name}.",
                )
            if record.error.code == "ambiguous_identity":
                return ClarificationDecision(
                    answer=self._ambiguous_identity_answer(record),
                    stop_reason="clarification_ambiguous_identity",
                    warning=f"Clarification required for ambiguous identity in {record.name}.",
                )
        return None

    def _ambiguous_identity_answer(self, record: ToolCallRecord) -> str:
        assert record.error is not None
        matches = record.error.details.get("matches")
        if not isinstance(matches, list) or not matches:
            return (
                "I found multiple matching identities. Please provide a unique object ID, "
                "user principal name, or group ID."
            )

        lines = ["I found multiple matching identities. Please choose one:"]
        for item in matches[:8]:
            if not isinstance(item, dict):
                continue
            label = item.get("displayName") or item.get("userPrincipalName") or item.get("mail") or item.get("id")
            identifiers = [
                value
                for value in (item.get("userPrincipalName"), item.get("mail"), item.get("id"))
                if value
            ]
            suffix = f" ({', '.join(identifiers)})" if identifiers else ""
            lines.append(f"- {label}{suffix}")
        return "\n".join(lines)

