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
