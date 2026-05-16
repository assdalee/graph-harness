from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


ToolErrorCode = Literal[
    "validation_error",
    "confirmation_required",
    "permission_denied",
    "not_found",
    "invalid_filter",
    "rate_limited",
    "transient_graph_error",
    "upstream_error",
    "unknown_tool",
    "ambiguous_identity",
]


class ToolError(BaseModel):
    code: ToolErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    ok: bool
    data: Any = None
    summary: str = ""
    identifiers: list[dict[str, Any]] = Field(default_factory=list)
    error: ToolError | None = None

    @classmethod
    def success(cls, data: Any, *, summary: str | None = None) -> "ToolResult":
        return cls(
            ok=True,
            data=data,
            summary=summary or summarize_payload(data),
            identifiers=extract_identifiers(data),
        )

    @classmethod
    def failure(
        cls,
        code: ToolErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> "ToolResult":
        return cls(
            ok=False,
            data=None,
            summary=message,
            identifiers=[],
            error=ToolError(code=code, message=message, details=details or {}),
        )

    @classmethod
    def from_payload(cls, payload: Any) -> "ToolResult":
        if isinstance(payload, ToolResult):
            return payload
        graph_error = _extract_graph_error(payload)
        if graph_error:
            return cls.failure(
                classify_error(graph_error.get("status_code"), graph_error.get("message", "")),
                str(graph_error.get("message") or "Microsoft Graph returned an error."),
                details={"payload": graph_error.get("payload") or payload},
            )
        return cls.success(payload)


def classify_error(status_code: int | None, message: str) -> ToolErrorCode:
    text = message.lower()
    if status_code in {401, 403} or "permission" in text or "authorization" in text:
        return "permission_denied"
    if status_code == 404 or "not found" in text:
        return "not_found"
    if status_code == 429 or "rate limit" in text or "too many requests" in text:
        return "rate_limited"
    if "filter" in text or "odata" in text or "unsupported" in text:
        return "invalid_filter"
    if status_code in {500, 502, 503, 504}:
        return "transient_graph_error"
    return "upstream_error"


def summarize_payload(payload: Any) -> str:
    records = extract_records(payload)
    if records is not None:
        if not records:
            return "Returned 0 records."
        first = records[0] if isinstance(records[0], dict) else {}
        keys = ", ".join(list(first.keys())[:8]) if isinstance(first, dict) else type(records[0]).__name__
        return f"Returned {len(records)} record(s). First record keys: {keys}."
    if isinstance(payload, dict):
        if payload.get("success") is True:
            return str(payload.get("message") or "Operation completed successfully.")
        keys = ", ".join(list(payload.keys())[:8])
        return f"Returned object with keys: {keys}."
    if payload is None:
        return "No data returned."
    return f"Returned {type(payload).__name__}."


def extract_records(payload: Any) -> list[Any] | None:
    if isinstance(payload, dict) and isinstance(payload.get("value"), list):
        return payload["value"]
    if isinstance(payload, list):
        return payload
    return None


IDENTIFIER_FIELDS = {
    "id",
    "userPrincipalName",
    "mail",
    "displayName",
    "groupId",
    "appId",
    "deviceId",
}


def extract_identifiers(payload: Any) -> list[dict[str, Any]]:
    records = extract_records(payload)
    source = records if records is not None else [payload]
    identifiers: list[dict[str, Any]] = []
    for item in source[:20]:
        if not isinstance(item, dict):
            continue
        row = {key: value for key, value in item.items() if key in IDENTIFIER_FIELDS and value}
        if row:
            identifiers.append(row)
    return identifiers


def _extract_graph_error(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or "error" not in payload:
        return None
    error = payload["error"]
    if isinstance(error, dict):
        return error
    return {"message": str(error)}

