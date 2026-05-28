from graph_harness.llm.profiles import resolve_profile


def test_native_anthropic_requires_tools_with_tool_history() -> None:
    assert resolve_profile("anthropic/claude-3-5-sonnet").requires_tools_with_tool_history
    assert resolve_profile("claude-opus-4-7").requires_tools_with_tool_history


def test_routed_anthropic_families_match() -> None:
    for model in (
        "openrouter/anthropic/claude-3.5-sonnet",
        "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
        "vertex_ai/claude-3-5-sonnet@20240620",
    ):
        assert resolve_profile(model).requires_tools_with_tool_history, model


def test_non_anthropic_models_use_default_profile() -> None:
    for model in ("openai/gpt-4o-mini", "gemini/gemini-1.5-pro", "ollama/llama3.1"):
        assert resolve_profile(model).requires_tools_with_tool_history is False, model


def test_override_forces_value_regardless_of_family() -> None:
    # Override on for a non-anthropic model.
    assert resolve_profile("openai/gpt-4o-mini", override=True).requires_tools_with_tool_history
    # Override off for an anthropic model.
    assert resolve_profile("claude-opus-4-7", override=False).requires_tools_with_tool_history is False


def test_case_insensitive_matching() -> None:
    assert resolve_profile("Anthropic/Claude-3-5-Sonnet").requires_tools_with_tool_history
