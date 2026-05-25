from graph_harness.core.config import Settings


def test_preferred_gateway_key_env(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setenv("API_GATEWAY_KEY", "gw-new")
    settings = Settings.from_env()
    assert settings.llm_api_key == "gw-new"
    assert settings.api_gateway_key == "gw-new"


def test_legacy_gateway_key_env_still_works(monkeypatch) -> None:
    monkeypatch.delenv("API_GATEWAY_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "gw-legacy")
    settings = Settings.from_env()
    assert settings.llm_api_key == "gw-legacy"


def test_preferred_takes_precedence_over_legacy_gateway(monkeypatch) -> None:
    monkeypatch.setenv("API_GATEWAY_KEY", "gw-new")
    monkeypatch.setenv("LLM_API_KEY", "gw-legacy")
    settings = Settings.from_env()
    assert settings.llm_api_key == "gw-new"


def test_preferred_provider_key_env(monkeypatch) -> None:
    monkeypatch.delenv("LLM_API_KEY_PROVIDER", raising=False)
    monkeypatch.setenv("LLM_PROVIDER_API_KEY", "prov-new")
    settings = Settings.from_env()
    assert settings.llm_api_key_provider == "prov-new"
    assert settings.llm_provider_api_key == "prov-new"


def test_legacy_provider_key_env_still_works(monkeypatch) -> None:
    monkeypatch.delenv("LLM_PROVIDER_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY_PROVIDER", "prov-legacy")
    settings = Settings.from_env()
    assert settings.llm_api_key_provider == "prov-legacy"
    assert settings.llm_provider_api_key == "prov-legacy"
