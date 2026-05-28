from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any

from pydantic import BaseModel


DEFAULT_JUDGE_MODEL = "anthropic/claude-3-5-sonnet-20241022"


def build_judge_model() -> Any:
    """Build a DeepEval-compatible judge model backed by LiteLLM.

    DeepEval imports are kept inside this eval-only module so the production app does not
    depend on DeepEval at import time.
    """
    try:
        from deepeval.models import DeepEvalBaseLLM
    except ImportError as exc:  # pragma: no cover - exercised only when eval deps are absent.
        raise RuntimeError(
            "DeepEval is not installed. Run `uv sync --extra dev --extra eval` first."
        ) from exc

    class LiteLLMDeepEvalJudge(DeepEvalBaseLLM):
        def __init__(self) -> None:
            self.model = os.getenv("DEEPEVAL_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
            self.temperature = _optional_float(os.getenv("DEEPEVAL_JUDGE_TEMPERATURE", "0"))
            self.timeout = float(os.getenv("DEEPEVAL_JUDGE_TIMEOUT_SECONDS", "90"))

        def load_model(self) -> str:
            return self.model

        def generate(self, prompt: str, schema: type[BaseModel] | None = None) -> Any:
            import litellm

            content = self._complete_sync(prompt, schema=schema, litellm=litellm)
            if schema is None:
                return content
            return _parse_schema_response(content, schema)

        async def a_generate(self, prompt: str, schema: type[BaseModel] | None = None) -> Any:
            import litellm

            content = await self._complete_async(prompt, schema=schema, litellm=litellm)
            if schema is None:
                return content
            return _parse_schema_response(content, schema)

        def get_model_name(self) -> str:
            return f"LiteLLM judge ({self.model})"

        def _base_kwargs(self, prompt: str) -> dict[str, Any]:
            kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "timeout": self.timeout,
            }
            if self.temperature is not None and not _model_deprecates_temperature(self.model):
                kwargs["temperature"] = self.temperature
            return kwargs

        def _complete_sync(
            self,
            prompt: str,
            *,
            schema: type[BaseModel] | None,
            litellm: Any,
        ) -> str:
            kwargs = self._base_kwargs(_schema_prompt(prompt, schema))
            raw = litellm.completion(**kwargs)
            return _message_content(raw)

        async def _complete_async(
            self,
            prompt: str,
            *,
            schema: type[BaseModel] | None,
            litellm: Any,
        ) -> str:
            kwargs = self._base_kwargs(_schema_prompt(prompt, schema))
            raw = await litellm.acompletion(**kwargs)
            return _message_content(raw)

    return LiteLLMDeepEvalJudge()


def ensure_judge_is_configured() -> None:
    model = os.getenv("DEEPEVAL_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
    if _is_anthropic_model(model) and not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "ANTHROPIC_API_KEY is required for the configured DeepEval judge model. "
            "Set ANTHROPIC_API_KEY or choose another DEEPEVAL_JUDGE_MODEL."
        )


def _optional_float(value: str | None) -> float | None:
    if value is None or value.strip().lower() in {"", "none", "null", "off"}:
        return None
    return float(value)


def _is_anthropic_model(model: str) -> bool:
    return model.startswith("anthropic/") or model.startswith("claude-")


def _model_deprecates_temperature(model: str) -> bool:
    normalized = (model or "").strip().lower()
    return "claude-opus-4-7" in normalized


def _schema_prompt(prompt: str, schema: type[BaseModel] | None) -> str:
    if schema is None:
        return prompt
    return (
        f"{prompt}\n\n"
        "Return only valid JSON matching this JSON Schema. Do not wrap the JSON in markdown.\n"
        f"{json.dumps(schema.model_json_schema(), indent=2)}"
    )


def _message_content(raw: Any) -> str:
    choices = _get(raw, "choices", []) or []
    if not choices:
        return ""
    message = _get(choices[0], "message", {}) or {}
    return str(_get(message, "content", "") or "")


def _parse_schema_response(content: str, schema: type[BaseModel]) -> BaseModel:
    try:
        return schema.model_validate_json(content)
    except Exception:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            raise
        return schema.model_validate_json(match.group(0))


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def run_sync(coro: Any) -> Any:
    return asyncio.run(coro)
