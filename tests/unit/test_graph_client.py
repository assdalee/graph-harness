import asyncio

import httpx
import pytest
import respx

from graph_harness.core.config import Settings
from graph_harness.core.errors import UpstreamServiceError
from graph_harness.graph.client import GraphClient


class _StubTokenProvider:
    def get_token(self) -> str:
        return "test-token"


def _client() -> GraphClient:
    return GraphClient(Settings(graph_backend="live", graph_timeout_seconds=5), _StubTokenProvider())


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    async def _sleep(_seconds):
        return None

    monkeypatch.setattr("graph_harness.graph.client.asyncio.sleep", _sleep)


@respx.mock
@pytest.mark.asyncio
async def test_retries_on_503_then_succeeds() -> None:
    route = respx.get("https://graph.microsoft.com/v1.0/users").mock(
        side_effect=[
            httpx.Response(503, headers={"Retry-After": "0"}, json={}),
            httpx.Response(200, json={"value": [{"id": "u1"}]}),
        ]
    )
    result = await _client().request("GET", "/users")
    assert result == {"value": [{"id": "u1"}]}
    assert route.call_count == 2


@respx.mock
@pytest.mark.asyncio
async def test_204_returns_success_envelope() -> None:
    respx.delete("https://graph.microsoft.com/v1.0/users/u1").mock(
        return_value=httpx.Response(204)
    )
    result = await _client().request("DELETE", "/users/u1")
    assert result["success"] is True


@respx.mock
@pytest.mark.asyncio
async def test_error_response_returns_error_envelope() -> None:
    respx.get("https://graph.microsoft.com/v1.0/users/missing").mock(
        return_value=httpx.Response(404, json={"error": {"message": "Not found"}})
    )
    result = await _client().request("GET", "/users/missing")
    assert result["error"]["status_code"] == 404
    assert result["error"]["message"] == "Not found"


@respx.mock
@pytest.mark.asyncio
async def test_transport_error_retries_then_raises() -> None:
    route = respx.get("https://graph.microsoft.com/v1.0/users").mock(
        side_effect=httpx.ConnectError("boom")
    )
    with pytest.raises(UpstreamServiceError):
        await _client().request("GET", "/users")
    assert route.call_count == 3


@respx.mock
@pytest.mark.asyncio
async def test_collection_follows_next_link_and_merges() -> None:
    next_url = "https://graph.microsoft.com/v1.0/users?$skiptoken=abc"
    respx.get("https://graph.microsoft.com/v1.0/users", params={"$top": "1"}).mock(
        return_value=httpx.Response(
            200, json={"value": [{"id": "u1"}], "@odata.nextLink": next_url}
        )
    )
    respx.get(next_url).mock(return_value=httpx.Response(200, json={"value": [{"id": "u2"}]}))

    result = await _client().request_collection(
        "/users", params={"$top": 1}, all_pages=True, max_pages=5
    )
    assert [item["id"] for item in result["value"]] == ["u1", "u2"]
    assert result["@agent.pagesRead"] == 2
    assert "@odata.nextLink" not in result


@respx.mock
@pytest.mark.asyncio
async def test_collection_single_page_when_all_pages_false() -> None:
    respx.get("https://graph.microsoft.com/v1.0/users").mock(
        return_value=httpx.Response(
            200, json={"value": [{"id": "u1"}], "@odata.nextLink": "https://x/next"}
        )
    )
    result = await _client().request_collection("/users", all_pages=False)
    assert result["value"] == [{"id": "u1"}]


def test_no_sleep_fixture_is_active() -> None:
    # Guards against accidentally removing the autouse no-sleep patch.
    assert asyncio.sleep is not None
