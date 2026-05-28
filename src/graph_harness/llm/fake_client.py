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
        if "upstream_error" in lowered or "transient_graph_error" in lowered:
            return LLMResponse(
                content=(
                    "Microsoft Graph returned an upstream error while executing the tool. "
                    "Check the Graph backend configuration and credentials, then retry."
                )
            )
        if "validation_error" in lowered:
            return LLMResponse(
                content="The tool arguments were invalid. Please make the request more specific."
            )
        return LLMResponse(
            content="The tool failed and mock recovery has no deterministic retry for this error."
        )

    def _final_from_messages(self, messages: list[dict[str, Any]]) -> str:
        latest_tool = self._latest_tool_result(messages)
        if latest_tool is not None:
            return self._final_from_tool(latest_tool)
        return "I could not find a tool result to answer from."

    def _final_from_tool(self, result: dict[str, Any]) -> str:
        if not result.get("ok", False):
            error = result.get("error") or {}
            return self._format_error(error)

        data = result.get("data")
        records = self._extract_records(data)
        if records is not None:
            return self._format_records(records)

        if isinstance(data, dict) and data.get("success") is True:
            return str(data.get("message") or "Operation completed successfully.")

        summary = result.get("summary") or "Tool completed."
        identifiers = result.get("identifiers") or []
        if identifiers:
            return f"{summary} Key identifiers: {self._format_identifiers(identifiers)}."
        return str(summary)

    @staticmethod
    def _format_error(error: dict[str, Any]) -> str:
        code = str(error.get("code") or "upstream_error")
        message = str(error.get("message") or "The tool call failed.")
        if code == "permission_denied":
            return (
                f"Microsoft Graph returned permission_denied: {message} "
                "The app likely needs additional Microsoft Graph permissions and admin consent."
            )
        return f"Microsoft Graph returned {code}: {message}"

    def _format_records(self, records: list[Any]) -> str:
        if not records:
            return "Returned 0 records."

        lines = [f"Returned {len(records)} record(s)."]
        for record in records[:3]:
            if not isinstance(record, dict):
                lines.append(f"- {record}")
                continue
            lines.append(f"- {self._format_record(record)}")
        return "\n".join(lines)

    @staticmethod
    def _format_record(record: dict[str, Any]) -> str:
        primary = str(
            record.get("title")
            or record.get("displayName")
            or record.get("userPrincipalName")
            or record.get("id")
            or "record"
        )
        details: list[str] = []
        for label, key in (
            ("id", "id"),
            ("severity", "severity"),
            ("status", "status"),
            ("UPN", "userPrincipalName"),
            ("mail", "mail"),
            ("appId", "appId"),
            ("scope", "scope"),
            ("created", "createdDateTime"),
        ):
            value = record.get(key)
            if value:
                details.append(f"{label}: {value}")
        return f"{primary} ({', '.join(details)})" if details else primary

    @staticmethod
    def _format_identifiers(identifiers: list[dict[str, Any]]) -> str:
        return "; ".join(
            ", ".join(f"{key}: {value}" for key, value in identifier.items())
            for identifier in identifiers[:5]
        )

    @staticmethod
    def _extract_records(data: Any) -> list[Any] | None:
        if isinstance(data, dict) and isinstance(data.get("value"), list):
            return data["value"]
        if isinstance(data, list):
            return data
        return None

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
