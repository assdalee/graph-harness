import pytest

from graph_harness.core.config import Settings
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.types import LLMToolCall
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import GraphToolFactory

TIER2_DOMAINS = {
    "secure_score",
    "ediscovery",
    "information_protection",
    "threat_intelligence",
    "online_meetings",
    "bookings",
    "search",
}


def build_registry():
    return GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()


def build_executor():
    return ToolExecutor(build_registry(), Settings(llm_model="openai/gpt-4o-mini"))


# --- registry / domains ----------------------------------------------------


def test_tier2_domains_registered() -> None:
    domains = {domain.name for domain in build_registry().list_domains()}
    assert TIER2_DOMAINS <= domains


def test_write_tools_are_gated() -> None:
    registry = build_registry()
    for name, domain in (
        ("close_ediscovery_case", "ediscovery"),
        ("create_online_meeting", "online_meetings"),
        ("create_booking_appointment", "bookings"),
    ):
        tool = registry.get(name)
        assert tool is not None, name
        assert tool.read_only is False, name
        assert tool.requires_confirmation is True, name
        assert tool.safety == "mutation", name
        assert tool.domain == domain, name


def test_read_only_domains_have_no_write_tools() -> None:
    registry = build_registry()
    for domain in ("secure_score", "information_protection", "threat_intelligence", "search"):
        tools = registry.tools_for_domain(domain)
        assert tools, domain
        assert all(tool.read_only for tool in tools), domain


# --- mock client routing (one representative read per domain) --------------


@pytest.mark.asyncio
async def test_mock_routes_one_read_per_domain() -> None:
    client = MockGraphClient()
    cases = [
        ("/security/secureScores", "value"),
        ("/security/cases/ediscoveryCases", "value"),
        ("/security/informationProtection/sensitivityLabels", "value"),
        ("/security/threatIntelligence/articles", "value"),
        ("/users/user-ada/onlineMeetings/meeting-1/attendanceReports", "value"),
        ("/solutions/bookingBusinesses", "value"),
    ]
    for endpoint, key in cases:
        result = await client.request("GET", endpoint)
        assert isinstance(result, dict) and result.get(key), endpoint


@pytest.mark.asyncio
async def test_get_by_id_routes() -> None:
    client = MockGraphClient()
    case = await client.request("GET", "/security/cases/ediscoveryCases/case-1")
    assert case["displayName"] == "Acme litigation"
    host = await client.request("GET", "/security/threatIntelligence/hosts/contoso.example")
    assert host["id"] == "contoso.example"
    meeting = await client.request("GET", "/users/user-ada/onlineMeetings/meeting-1")
    assert meeting["subject"] == "Customer sync"


@pytest.mark.asyncio
async def test_user_get_by_id_still_works() -> None:
    # The new /users/{id}/onlineMeetings/... routes must not shadow get-by-id.
    client = MockGraphClient()
    user = await client.request("GET", "/users/user-ada")
    assert user["displayName"] == "Ada Lovelace"


@pytest.mark.asyncio
async def test_search_query_routes_through_post() -> None:
    client = MockGraphClient()
    result = await client.request(
        "POST",
        "/search/query",
        json_data={"requests": [{"entityTypes": ["message"], "query": {"queryString": "q2"}}]},
    )
    assert result["value"][0]["hitsContainers"][0]["total"] == 1


# --- executor: reads run, writes are gated ---------------------------------


@pytest.mark.asyncio
async def test_list_secure_scores_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="list_secure_scores", args={})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_search_query_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="search_query", args={"query": "q2 planning"})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_create_online_meeting_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="create_online_meeting",
            args={
                "user_id": "user-ada",
                "subject": "Customer sync",
                "start_date_time": "2026-06-01T09:00:00Z",
                "end_date_time": "2026-06-01T10:00:00Z",
            },
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_create_online_meeting_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="create_online_meeting",
            args={
                "user_id": "user-ada",
                "subject": "Customer sync",
                "start_date_time": "2026-06-01T09:00:00Z",
                "end_date_time": "2026-06-01T10:00:00Z",
                "confirmed": True,
                "reason": "Scheduling the meeting the user asked for.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True
