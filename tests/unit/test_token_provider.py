import pytest

from graph_harness.core.config import Settings
from graph_harness.core.errors import AuthenticationError
from graph_harness.graph.auth import GraphTokenProvider


class _FakeMsalApp:
    instances: list["_FakeMsalApp"] = []

    def __init__(self, *args, **kwargs) -> None:
        self.acquire_calls = 0
        _FakeMsalApp.instances.append(self)

    def acquire_token_for_client(self, scopes):
        self.acquire_calls += 1
        return {"access_token": f"token-{self.acquire_calls}", "expires_in": 3600}


def _settings(**overrides) -> Settings:
    base = dict(
        graph_backend="live",
        graph_tenant_id="11111111-1111-1111-1111-111111111111",
        graph_client_id="22222222-2222-2222-2222-222222222222",
        graph_client_secret="secret-value",
    )
    base.update(overrides)
    return Settings(**base)


def test_missing_credentials_raises() -> None:
    provider = GraphTokenProvider(_settings(graph_tenant_id="", graph_client_id="", graph_client_secret=""))
    with pytest.raises(AuthenticationError):
        provider.get_token()


def test_token_is_acquired_and_cached(monkeypatch) -> None:
    _FakeMsalApp.instances.clear()
    monkeypatch.setattr("graph_harness.graph.auth.ConfidentialClientApplication", _FakeMsalApp)

    provider = GraphTokenProvider(_settings())
    first = provider.get_token()
    second = provider.get_token()

    assert first == "token-1"
    assert second == "token-1"  # cached; no second acquisition
    assert len(_FakeMsalApp.instances) == 1
    assert _FakeMsalApp.instances[0].acquire_calls == 1


def test_expired_token_is_refreshed(monkeypatch) -> None:
    _FakeMsalApp.instances.clear()
    monkeypatch.setattr("graph_harness.graph.auth.ConfidentialClientApplication", _FakeMsalApp)

    provider = GraphTokenProvider(_settings())
    provider.get_token()
    # Force expiry, then the next call must re-acquire.
    provider._expires_at = 0.0
    second = provider.get_token()

    assert second == "token-2"
    assert _FakeMsalApp.instances[0].acquire_calls == 2


def test_failed_acquisition_raises(monkeypatch) -> None:
    class _FailingApp:
        def __init__(self, *a, **k) -> None: ...

        def acquire_token_for_client(self, scopes):
            return {"error": "invalid_client", "error_description": "bad secret"}

    monkeypatch.setattr("graph_harness.graph.auth.ConfidentialClientApplication", _FailingApp)
    provider = GraphTokenProvider(_settings())
    with pytest.raises(AuthenticationError):
        provider.get_token()
