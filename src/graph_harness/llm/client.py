"""LiteLLM adapter — the single provider boundary.

The rest of the app speaks exactly one message format: LiteLLM's
OpenAI-compatible chat format (a list of ``{"role", "content", ...}`` dicts,
with tool calls under ``tool_calls[].function`` and tool results as
``{"role": "tool", ...}`` messages). LiteLLM translates that to and from each
underlying provider's wire format (Anthropic, Gemini, Bedrock, Ollama, ...),
so the app never builds provider-specific payloads itself.

Keep all provider-specific request shaping here and in ``profiles.py``. Do not
add per-provider branches elsewhere, and do not add a second message
converter — LiteLLM already is that layer.
"""

import json
from typing import Any

from graph_harness.core.config import Settings
from graph_harness.llm.profiles import resolve_profile
from graph_harness.llm.types import LLMResponse, LLMToolCall


class LiteLLMClient:
    """Small async adapter around LiteLLM.

    This is the only place in the application that should know LiteLLM response shapes.
    """

    def __init__(self, settings: Settings) -> None:
        """Store settings used to build LiteLLM completion requests."""
        self._settings = settings

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = "auto",
    ) -> LLMResponse:
        """Call LiteLLM for one completion, applying provider quirks and a retry workaround."""
        try:
            import litellm
        except ImportError as exc:
            raise RuntimeError(
                "LiteLLM is not installed. Install project dependencies with "
                "`pip install -e .` or `pip install litellm`."
            ) from exc

        profile = resolve_profile(
            self._settings.llm_model,
            override=self._settings.llm_requires_tools_with_tool_history,
        )

        kwargs = self._completion_kwargs(messages)
        if tools is not None:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice
        elif profile.requires_tools_with_tool_history and _has_tool_history(messages):
            kwargs["tools"] = [_finalization_tool()]
            kwargs["tool_choice"] = "none"

        try:
            raw = await litellm.acompletion(**kwargs)
        except Exception as exc:
            # Safety net for the long tail: if a provider rejects a tool-history
            # request for lack of a tools field and our profile did not already
            # adapt, apply the workaround once and retry. This self-heals models
            # the registry does not yet know about.
            if (
                "tools" not in kwargs
                and _has_tool_history(messages)
                and _looks_like_missing_tools_error(exc)
            ):
                kwargs["tools"] = [_finalization_tool()]
                kwargs["tool_choice"] = "none"
                raw = await litellm.acompletion(**kwargs)
            else:
                raise
        return self._normalize_response(raw)

    def _completion_kwargs(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        """Assemble the base LiteLLM request kwargs from settings and messages."""
        kwargs: dict[str, Any] = {
            "model": self._settings.llm_model,
            "messages": messages,
            "max_tokens": self._settings.litellm_max_tokens,
            "timeout": self._settings.litellm_timeout_seconds,
            # Let LiteLLM strip params (e.g. temperature) for models that reject
            # them, instead of us blanket-dropping them for every model.
            "drop_params": True,
        }
        if self._settings.litellm_temperature is not None:
            kwargs["temperature"] = self._settings.litellm_temperature
        if self._settings.litellm_api_base:
            kwargs["api_base"] = self._settings.litellm_api_base
        resolved_key = self._resolve_provider_api_key()
        if resolved_key:
            kwargs["api_key"] = resolved_key
        return kwargs

    def _resolve_provider_api_key(self) -> str | None:
        """Pick the provider API key based on the configured model.

        OpenRouter keys (``openrouter/...`` models) take precedence over the
        generic ``LLM_API_KEY_PROVIDER`` when both are set.
        """
        model = (self._settings.llm_model or "").lower()
        if model.startswith("openrouter/") and self._settings.openrouter_api_key:
            return self._settings.openrouter_api_key
        return self._settings.llm_api_key_provider

    def _normalize_response(self, raw: Any) -> LLMResponse:
        """Convert a raw LiteLLM response into the app's LLMResponse shape."""
        # The single place that reads a provider response. LiteLLM normalizes
        # every provider to the OpenAI shape (``choices[].message``), so we only
        # read that shape. ``_get`` bridges the two concrete forms it arrives
        # in: typed objects from LiteLLM at runtime, plain dicts in tests.
        choice = self._first_choice(raw)
        message = self._get(choice, "message", {}) or {}
        content = self._get(message, "content", "") or ""
        raw_tool_calls = self._get(message, "tool_calls", []) or []
        tool_calls = [self._normalize_tool_call(item, index) for index, item in enumerate(raw_tool_calls)]
        return LLMResponse(content=str(content), tool_calls=tool_calls, raw=raw)

    def _normalize_tool_call(self, raw: Any, index: int) -> LLMToolCall:
        """Convert one raw tool call into an LLMToolCall, synthesizing an id if missing."""
        # LiteLLM guarantees the OpenAI tool-call shape: name and arguments live
        # under ``function``, so no top-level fallback is needed.
        call_id = self._get(raw, "id", None) or f"tool_call_{index + 1}"
        function = self._get(raw, "function", {}) or {}
        name = self._get(function, "name", "")
        args = self._parse_args(self._get(function, "arguments", {}))
        return LLMToolCall(id=str(call_id), name=str(name), args=args)

    @staticmethod
    def _parse_args(value: Any) -> dict[str, Any]:
        """Coerce tool-call arguments (dict or JSON string) into a dict, defaulting to empty."""
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    @staticmethod
    def _first_choice(raw: Any) -> Any:
        """Return the first choice from a response, or an empty dict if none."""
        choices = LiteLLMClient._get(raw, "choices", []) or []
        return choices[0] if choices else {}

    @staticmethod
    def _get(obj: Any, key: str, default: Any = None) -> Any:
        """Read a field from either a dict or an attribute object, bridging LiteLLM's two forms."""
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)


def _has_tool_history(messages: list[dict[str, Any]]) -> bool:
    """Report whether the conversation already contains tool calls or results."""
    for message in messages:
        if message.get("role") == "tool":
            return True
        if message.get("role") == "assistant" and message.get("tool_calls"):
            return True
    return False


def _looks_like_missing_tools_error(exc: Exception) -> bool:
    """Heuristically detect a provider error caused by tool history without a tools field."""
    text = str(exc).lower()
    if "tool" not in text:
        return False
    signals = ("tool_use", "tool_result", "tools` is", "tools field", "tools is required", "no tools")
    return any(signal in text for signal in signals) or ("tools" in text and "required" in text)


def _finalization_tool() -> dict[str, Any]:
    """Return a placeholder tool schema that satisfies providers requiring tools with tool history."""
    return {
        "type": "function",
        "function": {
            "name": "final_answer_context",
            "description": (
                "Placeholder tool schema required by Anthropic when prior tool results are "
                "present. Do not call this tool; write the final answer instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    }
