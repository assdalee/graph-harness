from fastapi.testclient import TestClient

from graph_harness.app.main import create_app
from graph_harness.core.config import Settings


def _client(**overrides) -> TestClient:
    settings = Settings(graph_backend="mock", llm_backend="fake", **overrides)
    return TestClient(create_app(settings))


def test_wildcard_origin_disables_credentials() -> None:
    app = create_app(
        Settings(
            graph_backend="mock",
            llm_backend="fake",
            cors_allow_origins=["*"],
            cors_allow_credentials=True,
        )
    )
    cors = next(m for m in app.user_middleware if "CORSMiddleware" in str(m))
    assert cors.kwargs["allow_credentials"] is False
    assert cors.kwargs["allow_origins"] == ["*"]


def test_explicit_origin_allows_credentials() -> None:
    app = create_app(
        Settings(
            graph_backend="mock",
            llm_backend="fake",
            cors_allow_origins=["https://console.example.com"],
            cors_allow_credentials=True,
        )
    )
    cors = next(m for m in app.user_middleware if "CORSMiddleware" in str(m))
    assert cors.kwargs["allow_credentials"] is True
    assert cors.kwargs["allow_origins"] == ["https://console.example.com"]


def test_cors_origins_parsed_from_csv_env(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://a.example.com, https://b.example.com")
    settings = Settings.from_env()
    assert settings.cors_allow_origins == ["https://a.example.com", "https://b.example.com"]


def test_api_key_gate_rejects_invalid_key() -> None:
    client = _client(llm_api_key="secret")
    response = client.get("/v1/graph/operations", headers={"x-api-key": "wrong"})
    assert response.status_code == 403


def test_api_key_gate_accepts_valid_key() -> None:
    client = _client(llm_api_key="secret")
    response = client.get("/v1/graph/operations", headers={"x-api-key": "secret"})
    assert response.status_code == 200


def test_api_key_gate_open_when_unset() -> None:
    client = _client()
    response = client.get("/v1/graph/operations")
    assert response.status_code == 200
