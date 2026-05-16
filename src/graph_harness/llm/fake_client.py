from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from graph_harness.core.config import Settings
from graph_harness.llm.types import LLMResponse, LLMToolCall


class FakeLLMClient:
    """Deterministic local LLM stand-in for no-credential evals.

    It is intentionally small and transparent. It does not try to be smart; it maps common eval
    prompts to tool calls and turns tool result envelopes into simple final answers.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._scenarios = self._load_scenarios(settings.llm_fake_scenarios_path if settings else None)

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = "auto",
    ) -> LLMResponse:
        if tools is None:
            return LLMResponse(content=self._final_from_messages(messages))

        recovery_message = self._latest_recovery_message(messages)
        if recovery_message:
            return self._recover(recovery_message)

        latest_tool = self._latest_tool_result(messages)
        if latest_tool is not None:
            return LLMResponse(content=self._final_from_tool(latest_tool))

        user_text = self._latest_user_text(messages)
        scenario_response = self._scenario_tool_call(user_text)
        if scenario_response is not None:
            return scenario_response
        return self._tool_call_for_user_text(user_text)

    def _tool_call_for_user_text(self, text: str) -> LLMResponse:
        lowered = text.lower()
        if "bad filter" in lowered or "unsupported filter" in lowered:
            return self._call(
                "list_security_alerts",
                {"filter_expression": "badUnsupported eq 'x'", "top": 10},
            )
        if "rate limit" in lowered:
            return self._call("list_users", {"filter_expression": "rateLimit eq 'true'", "top": 10})
        if "incident" in lowered and "permission" in lowered:
            return self._call("graph_operation", {"operation_name": "list_security_incidents"})
        if "delete" in lowered and "oauth" in lowered:
            args = {"grant_id": "grant-risky"}
            if "confirmed" in lowered:
                args.update(
                    {
                        "confirmed": True,
                        "reason": "Mock eval confirmed OAuth grant deletion.",
                        "target_display": "Risky OAuth grant",
                    }
                )
            return self._call("delete_oauth_permission_grant", args)
        if "oauth" in lowered and "grant" in lowered:
            return self._call("list_oauth_permission_grants", {"top": 10})
        if "service principal" in lowered or "service principals" in lowered:
            return self._call("list_service_principals", {"top": 10})
        if "revoke" in lowered and "session" in lowered:
            args = {"user_id": "user-sarah"}
            if "confirmed" in lowered:
                args.update(
                    {
                        "confirmed": True,
                        "reason": "Mock eval confirmed session revocation.",
                        "target_display": "Sarah Chen",
                    }
                )
            return self._call("revoke_user_sessions", args)
        if "add" in lowered and "finance" in lowered:
            return self._call(
                "add_group_member",
                {
                    "group_id": "group-finance",
                    "member_id": "user-ada",
                    "confirmed": True,
                    "reason": "Mock eval confirmed group membership change.",
                    "target_display": "Ada Lovelace -> Finance",
                },
            )
        if "missing sarah" in lowered:
            return self._call("get_user", {"user_id": "missing-sarah"})
        if "high" in lowered and "alert" in lowered:
            return self._call("list_security_alerts", {"severity": "high", "top": 10})
        if "failed" in lowered and "sign" in lowered:
            return self._call("list_sign_in_logs", {"status_error_code": 50126, "top": 10})
        if "resolve" in lowered or "find" in lowered:
            if "alex" in lowered:
                return self._call("resolve_user", {"query": "Alex Kim"})
            if "sarah" in lowered:
                return self._call("resolve_user", {"query": "Sarah Chen"})
            if "finance" in lowered:
                return self._call("resolve_group", {"query": "Finance"})
        if "list" in lowered and "group" in lowered:
            return self._call("list_groups", {"top": 10})
        return self._call("list_users", {"top": 10})

    def _recover(self, recovery_message: str) -> LLMResponse:
        lowered = recovery_message.lower()
        if "invalid_filter" in lowered:
            return self._call("list_security_alerts", {"severity": "high", "top": 10})
        if "not_found" in lowered and "resolve_user" in lowered:
            return self._call("resolve_user", {"query": "Sarah Chen"})
        if "rate_limited" in lowered:
            return self._call("list_users", {"top": 1})
        return LLMResponse(content="I cannot safely recover from that tool error in mock mode.")

    def _final_from_messages(self, messages: list[dict[str, Any]]) -> str:
        latest_tool = self._latest_tool_result(messages)
        if latest_tool is not None:
            return self._final_from_tool(latest_tool)
        return "Mock final answer: no tool results were available."

    def _final_from_tool(self, result: dict[str, Any]) -> str:
        if not result.get("ok", False):
            error = result.get("error") or {}
            return f"Mock final answer: tool failed with {error.get('code')}: {error.get('message')}"
        summary = result.get("summary") or "Tool completed."
        identifiers = result.get("identifiers") or []
        if identifiers:
            return f"Mock final answer: {summary} Identifiers: {identifiers}"
        return f"Mock final answer: {summary}"

    def _call(self, name: str, args: dict[str, Any]) -> LLMResponse:
        return LLMResponse(tool_calls=[LLMToolCall(id=f"fake_{name}", name=name, args=args)])

    def _scenario_tool_call(self, text: str) -> LLMResponse | None:
        lowered = text.lower()
        for scenario in self._scenarios:
            match = str(scenario.get("match") or "").lower()
            if not match or match not in lowered:
                continue
            tool = scenario.get("tool")
            if not tool:
                continue
            return self._call(str(tool), dict(scenario.get("args") or {}))
        return None

    @staticmethod
    def _load_scenarios(path: str | None) -> list[dict[str, Any]]:
        if not path:
            return []
        scenario_path = Path(path)
        if not scenario_path.exists():
            return []
        payload = json.loads(scenario_path.read_text())
        return payload if isinstance(payload, list) else []

    @staticmethod
    def _latest_user_text(messages: list[dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return str(message.get("content") or "")
        return ""

    @staticmethod
    def _latest_recovery_message(messages: list[dict[str, Any]]) -> str | None:
        for message in reversed(messages):
            if message.get("role") == "tool":
                return None
            if message.get("role") == "user" and "Recovery policy instruction" in str(message.get("content")):
                return str(message.get("content"))
        return None

    @staticmethod
    def _latest_tool_result(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
        for message in reversed(messages):
            if message.get("role") != "tool":
                continue
            try:
                payload = json.loads(str(message.get("content") or "{}"))
            except json.JSONDecodeError:
                return None
            return payload if isinstance(payload, dict) else None
        return None
