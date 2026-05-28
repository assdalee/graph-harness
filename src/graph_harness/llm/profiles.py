"""Declarative per-model capability profiles for provider-specific request shaping."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class ModelProfile:
    """Declarative capabilities/quirks for a model family.

    Add a flag here (not an ``if`` in the request path) when a provider needs
    special request shaping that LiteLLM cannot infer on its own.
    """

    requires_tools_with_tool_history: bool = False


_DEFAULT = ModelProfile()


@lru_cache(maxsize=256)
def _provider_of(model: str) -> str | None:
    """Best-effort provider name from LiteLLM's registry.

    Used as an additive signal for family detection. Defensive: any failure
    (unknown model, import error) yields None so detection falls back to the
    string heuristics below and never regresses. Cached because LiteLLM does
    real work (and emits noise) for unrecognized models.
    """
    try:
        import litellm

        litellm.suppress_debug_info = True
        return litellm.get_llm_provider(model)[1]
    except Exception:
        return None


def _is_anthropic_family(model: str) -> bool:
    """Detect Anthropic-family models across providers via name heuristics and a provider probe."""
    # Native Anthropic (anthropic/claude-...), bare (claude-...), Bedrock
    # (bedrock/anthropic.claude-...), Vertex (vertex_ai/claude-...), and
    # OpenRouter (openrouter/anthropic/...) all surface the Anthropic quirk
    # where a request carrying tool history must also include the tools field.
    # The string check catches router-prefixed models (where LiteLLM reports
    # the router as the provider); the provider probe catches native Anthropic
    # aliases whose name does not contain "claude"/"anthropic".
    if "claude" in model or "anthropic" in model:
        return True
    return _provider_of(model) == "anthropic"


# Ordered (matcher, profile) rules. This is the ONLY place model name patterns
# live; everything else asks ``resolve_profile``.
_RULES: list[tuple[Callable[[str], bool], ModelProfile]] = [
    (_is_anthropic_family, ModelProfile(requires_tools_with_tool_history=True)),
]


def resolve_profile(model: str, *, override: bool | None = None) -> ModelProfile:
    """Resolve the capability profile for ``model``.

    Precedence: an explicit settings ``override`` wins (operator escape hatch,
    no code change), then the first matching rule, then the default profile.
    """
    if override is not None:
        return ModelProfile(requires_tools_with_tool_history=override)
    normalized = (model or "").strip().lower()
    for matches, profile in _RULES:
        if matches(normalized):
            return profile
    return _DEFAULT
