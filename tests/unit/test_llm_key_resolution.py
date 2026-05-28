import pytest

from graph_harness.core.config import Settings
from graph_harness.llm.client import LiteLLMClient


def test_resolves_openrouter_key_for_openrouter_model() -> None:
    settings = Settings(
        llm_model="openrouter/anthropic/claude-3.5-sonnet",
        openrouter_api_key="sk-or-test",
        llm_api_key_provider="sk-direct",
    )

    client = LiteLLMClient(settings)

    assert client._resolve_provider_api_key() == "sk-or-test"


def test_falls_back_to_provider_key_when_openrouter_key_missing() -> None:
    settings = Settings(
        llm_model="openrouter/anthropic/claude-3.5-sonnet",
        openrouter_api_key=None,
        llm_api_key_provider="sk-direct",
    )

    client = LiteLLMClient(settings)

    assert client._resolve_provider_api_key() == "sk-direct"


def test_uses_provider_key_for_direct_model() -> None:
    settings = Settings(
        llm_model="openai/gpt-4o-mini",
        openrouter_api_key="sk-or-test",
        llm_api_key_provider="sk-direct",
    )

    client = LiteLLMClient(settings)

    assert client._resolve_provider_api_key() == "sk-direct"


def test_returns_none_when_no_keys_configured() -> None:
    settings = Settings(llm_model="openai/gpt-4o-mini")

    client = LiteLLMClient(settings)

    assert client._resolve_provider_api_key() is None


def test_settings_reads_openrouter_key_from_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-env")

    settings = Settings.from_env()

    assert settings.openrouter_api_key == "sk-or-env"


def test_openrouter_key_match_is_case_insensitive() -> None:
    settings = Settings(
        llm_model="OpenRouter/anthropic/claude-3.5-sonnet",
        openrouter_api_key="sk-or-test",
    )

    client = LiteLLMClient(settings)

    assert client._resolve_provider_api_key() == "sk-or-test"


def test_runtime_completion_kwargs_do_not_send_temperature() -> None:
    settings = Settings(llm_model="openai/gpt-4o-mini")

    client = LiteLLMClient(settings)

    kwargs = client._completion_kwargs([{"role": "user", "content": "hello"}])
    assert "temperature" not in kwargs


@pytest.mark.asyncio
async def test_adds_disabled_dummy_tool_for_anthropic_tool_history(monkeypatch) -> None:
    captured: dict = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return {"choices": [{"message": {"content": "done"}}]}

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    settings = Settings(llm_model="claude-opus-4-7")
    client = LiteLLMClient(settings)

    response = await client.complete(
        messages=[
            {"role": "assistant", "content": "", "tool_calls": [{"id": "call-1"}]},
            {"role": "tool", "tool_call_id": "call-1", "content": "{}"},
            {"role": "user", "content": "Write final answer."},
        ],
        tools=None,
        tool_choice=None,
    )

    assert response.content == "done"
    assert captured["tool_choice"] == "none"
    assert captured["tools"][0]["function"]["name"] == "final_answer_context"
    assert "temperature" not in captured


@pytest.mark.asyncio
async def test_does_not_add_dummy_tool_without_tool_history(monkeypatch) -> None:
    captured: dict = {}

    async def fake_acompletion(**kwargs):
        captured.update(kwargs)
        return {"choices": [{"message": {"content": "done"}}]}

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    settings = Settings(llm_model="claude-opus-4-7")
    client = LiteLLMClient(settings)

    await client.complete(messages=[{"role": "user", "content": "hello"}], tools=None)

    assert "tools" not in captured
    assert "tool_choice" not in captured
