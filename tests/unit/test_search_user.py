import pytest

from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.tools.graph_tools import GraphToolFactory, SearchUserArgs


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def request(self, method, endpoint, **kwargs):
        self.calls.append({"method": method, "endpoint": endpoint, **kwargs})
        return {"value": []}

    async def request_collection(self, endpoint, **kwargs):
        self.calls.append({"method": "GET", "endpoint": endpoint, **kwargs})
        return {"value": []}


def _factory() -> tuple[GraphToolFactory, _RecordingClient]:
    client = _RecordingClient()
    return GraphToolFactory(client, GraphOperationCatalog.default()), client


@pytest.mark.asyncio
async def test_search_user_uses_prefix_filter() -> None:
    factory, client = _factory()
    await factory.search_user(SearchUserArgs(query="Sar", top=5))

    call = client.calls[-1]
    filter_expr = call["params"]["$filter"]
    assert "startswith(displayName,'Sar')" in filter_expr
    assert "startswith(userPrincipalName,'Sar')" in filter_expr
    assert "startswith(mail,'Sar')" in filter_expr
    assert "eq '" not in filter_expr


@pytest.mark.asyncio
async def test_search_user_requests_advanced_query() -> None:
    factory, client = _factory()
    await factory.search_user(SearchUserArgs(query="Sar"))
    assert client.calls[-1]["advanced_query"] is True


@pytest.mark.asyncio
async def test_search_user_escapes_quotes() -> None:
    factory, client = _factory()
    await factory.search_user(SearchUserArgs(query="O'Brien"))
    assert "O''Brien" in client.calls[-1]["params"]["$filter"]
