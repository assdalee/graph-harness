from __future__ import annotations

import json
from typing import Any

from graph_harness.core.config import Settings


class ContextCompactor:
    """Build a compact, identifier-preserving message view for LLM calls."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def compact(self, messages: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
        if not self._settings.agent_enable_context_compaction:
            return messages, False

        # Keep small conversations verbatim to avoid unnecessary prompt churn.
        if len(messages) <= self._settings.agent_context_recent_messages + 2:
            return messages, False

        system_messages = [message for message in messages if message.get("role") == "system"]
        first_user = next((message for message in messages if message.get("role") == "user"), None)
        split = len(messages) - self._settings.agent_context_recent_messages
        omitted = messages[:split]
        recent = messages[split:]
        summary = self._build_summary(omitted)

        compacted: list[dict[str, Any]] = []
        if system_messages:
            compacted.append(system_messages[0])
        if first_user and first_user not in compacted:
            compacted.append(
                {
                    "role": "user",
                    "content": f"Original user intent: {first_user.get('content', '')}",
                }
            )
        if summary:
            compacted.append({"role": "system", "content": summary})
        compacted.extend(recent)
        return compacted, True

    def _build_summary(self, messages: list[dict[str, Any]]) -> str:
        tool_summaries: list[str] = []
        assistant_notes: list[str] = []
        recovery_or_clarification: list[str] = []

        for message in messages:
            role = message.get("role")
            content = str(message.get("content") or "")
            if role == "tool":
                tool_summaries.append(self._summarize_tool_message(message))
            elif role == "assistant" and content:
                assistant_notes.append(_truncate(content, 240))
            elif role == "user" and (
                "Recovery policy instruction" in content
                or "empty" in content.lower()
                or "clarification" in content.lower()
            ):
                recovery_or_clarification.append(_truncate(content, 360))

        parts = ["Compacted prior context:"]
        if assistant_notes:
            parts.append("Assistant notes:")
            parts.extend(f"- {item}" for item in assistant_notes[-4:])
        if tool_summaries:
            parts.append("Tool results:")
            parts.extend(f"- {item}" for item in tool_summaries[-8:])
        if recovery_or_clarification:
            parts.append("Recovery/clarification directives:")
            parts.extend(f"- {item}" for item in recovery_or_clarification[-4:])
        return _truncate("\n".join(parts), self._settings.agent_context_max_tool_chars)

    def _summarize_tool_message(self, message: dict[str, Any]) -> str:
        name = message.get("name") or "tool"
        try:
            payload = json.loads(str(message.get("content") or "{}"))
        except json.JSONDecodeError:
            return f"{name}: {_truncate(str(message.get('content') or ''), 220)}"

        if not isinstance(payload, dict):
            return f"{name}: returned {type(payload).__name__}."

        ok = payload.get("ok")
        summary = payload.get("summary") or ""
        identifiers = payload.get("identifiers") or []
        error = payload.get("error") or {}
        if ok is False:
            code = error.get("code")
            message_text = error.get("message")
            return _truncate(f"{name}: error {code}: {message_text}", 360)
        id_text = f" identifiers={identifiers[:8]}" if identifiers else ""
        return _truncate(f"{name}: {summary}{id_text}", 420)


def _truncate(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]} ...[truncated]"

