from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelProfile:
    """Declarative capabilities/quirks for a model family.

    Add a flag here (not an ``if`` in the request path) when a provider needs
    special request shaping that LiteLLM cannot infer on its own.
    """

    requires_tools_with_tool_history: bool = False


_DEFAULT = ModelProfile()


def _is_anthropic_family(model: str) -> bool:
    # Native Anthropic (anthropic/claude-...), bare (claude-...), Bedrock
    # (bedrock/anthropic.claude-...), Vertex (vertex_ai/claude-...), and
    # OpenRouter (openrouter/anthropic/...) all surface the Anthropic quirk
    # where a request carrying tool history must also include the tools field.
    return "claude" in model or "anthropic" in model


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
