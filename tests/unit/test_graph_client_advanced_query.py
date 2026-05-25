import httpx
import pytest
import respx

from graph_harness.core.config import Settings
from graph_harness.graph.client import GraphClient


class _StubTokenProvider:
    def get_token(self) -> str:
        return "test-token"


def _client() -> GraphClient:
    return GraphClient(Settings(graph_backend="live", graph_timeout_seconds=5), _StubTokenProvider())


@respx.mock
@pytest.mark.asyncio
async def test_advanced_query_sends_consistency_level_header() -> None:
    route = respx.get("https://graph.microsoft.com/v1.0/users").mock(
        return_value=httpx.Response(200, json={"value": []})
    )
    await _client().request("GET", "/users", advanced_query=True)
    assert route.calls.last.request.headers["ConsistencyLevel"] == "eventual"


@respx.mock
@pytest.mark.asyncio
async def test_standard_query_omits_consistency_level_header() -> None:
    route = respx.get("https://graph.microsoft.com/v1.0/users").mock(
        return_value=httpx.Response(200, json={"value": []})
    )
    await _client().request("GET", "/users")
    assert "ConsistencyLevel" not in route.calls.last.request.headers


@respx.mock
@pytest.mark.asyncio
async def test_collection_propagates_advanced_query_to_pages() -> None:
    next_url = "https://graph.microsoft.com/v1.0/users?$skiptoken=abc"
    respx.get("https://graph.microsoft.com/v1.0/users", params={"$count": "true"}).mock(
        return_value=httpx.Response(
            200, json={"value": [{"id": "u1"}], "@odata.nextLink": next_url}
        )
    )
    page_two = respx.get(next_url).mock(
        return_value=httpx.Response(200, json={"value": [{"id": "u2"}]})
    )
    await _client().request_collection(
        "/users", params={"$count": "true"}, all_pages=True, max_pages=5, advanced_query=True
    )
    assert page_two.calls.last.request.headers["ConsistencyLevel"] == "eventual"
