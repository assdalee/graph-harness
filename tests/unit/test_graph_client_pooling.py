import httpx
import pytest

from graph_harness.core.config import Settings
from graph_harness.graph.client import GraphClient


class _StubTokenProvider:
    def get_token(self) -> str:
        return "test-token"


def _client() -> GraphClient:
    return GraphClient(Settings(graph_backend="live"), _StubTokenProvider())


@pytest.mark.asyncio
async def test_reuses_single_http_client() -> None:
    client = _client()
    first = client._http_client()
    second = client._http_client()
    assert first is second
    await client.aclose()


@pytest.mark.asyncio
async def test_aclose_closes_and_allows_recreate() -> None:
    client = _client()
    instance = client._http_client()
    assert isinstance(instance, httpx.AsyncClient)
    await client.aclose()
    assert instance.is_closed
    # A subsequent call recreates a fresh client rather than reusing a closed one.
    recreated = client._http_client()
    assert recreated is not instance
    assert not recreated.is_closed
    await client.aclose()


@pytest.mark.asyncio
async def test_aclose_is_idempotent() -> None:
    client = _client()
    client._http_client()
    await client.aclose()
    await client.aclose()
