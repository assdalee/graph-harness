import pytest

from graph_harness.graph.mock_client import MockGraphClient


@pytest.fixture
def client() -> MockGraphClient:
    return MockGraphClient()


@pytest.mark.asyncio
async def test_list_users_returns_all(client) -> None:
    result = await client.request("GET", "/users")
    ids = {u["id"] for u in result["value"]}
    assert {"user-ada", "user-sarah"} <= ids


@pytest.mark.asyncio
async def test_user_filter_matches_display_name(client) -> None:
    result = await client.request(
        "GET", "/users", params={"$filter": "displayName eq 'Sarah Chen'"}
    )
    assert [u["id"] for u in result["value"]] == ["user-sarah"]


@pytest.mark.asyncio
async def test_get_user_by_id(client) -> None:
    result = await client.request("GET", "/users/user-ada")
    assert result["displayName"] == "Ada Lovelace"


@pytest.mark.asyncio
async def test_get_unknown_user_returns_404(client) -> None:
    result = await client.request("GET", "/users/nope")
    assert result["error"]["status_code"] == 404


@pytest.mark.asyncio
async def test_high_severity_alerts_filtered(client) -> None:
    result = await client.request(
        "GET", "/security/alerts_v2", params={"$filter": "severity eq 'high'"}
    )
    assert [a["id"] for a in result["value"]] == ["alert-1"]


@pytest.mark.asyncio
async def test_security_incidents_denied(client) -> None:
    result = await client.request("GET", "/security/incidents")
    assert result["error"]["status_code"] == 403


@pytest.mark.asyncio
async def test_rate_limit_filter_triggers_error(client) -> None:
    result = await client.request(
        "GET", "/users", params={"$filter": "rateLimit eq 'true'"}
    )
    assert result["error"]["status_code"] == 429


@pytest.mark.asyncio
async def test_unsupported_alert_filter_is_400(client) -> None:
    result = await client.request(
        "GET", "/security/alerts_v2", params={"$filter": "badUnsupported eq 'x'"}
    )
    assert result["error"]["status_code"] == 400


@pytest.mark.asyncio
async def test_oauth_grants_listed(client) -> None:
    result = await client.request("GET", "/oauth2PermissionGrants")
    assert [g["id"] for g in result["value"]] == ["grant-risky"]


@pytest.mark.asyncio
async def test_top_limits_results(client) -> None:
    result = await client.request("GET", "/users", params={"$top": 1})
    assert len(result["value"]) == 1


@pytest.mark.asyncio
async def test_delete_oauth_grant_succeeds(client) -> None:
    result = await client.request("DELETE", "/oauth2PermissionGrants/grant-risky")
    assert result["success"] is True


@pytest.mark.asyncio
async def test_advanced_query_is_accepted(client) -> None:
    # search_user passes advanced_query=True; the mock must accept it like the live client.
    result = await client.request("GET", "/users", advanced_query=True)
    assert {u["id"] for u in result["value"]} >= {"user-ada", "user-sarah"}
    page = await client.request_collection("/users", advanced_query=True)
    assert "value" in page
