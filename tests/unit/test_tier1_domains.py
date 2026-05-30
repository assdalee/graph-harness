import pytest

from graph_harness.core.config import Settings
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.types import LLMToolCall
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import GraphToolFactory

TIER1_DOMAINS = {
    "chats",
    "sharepoint_sites",
    "onenote",
    "contacts",
    "planner",
    "todo",
    "usage_reports",
    "service_health",
}


def build_registry():
    return GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()


def build_executor():
    return ToolExecutor(build_registry(), Settings(llm_model="openai/gpt-4o-mini"))


# --- registry / domains ----------------------------------------------------


def test_tier1_domains_registered() -> None:
    domains = {domain.name for domain in build_registry().list_domains()}
    assert TIER1_DOMAINS <= domains


def test_write_tools_are_gated() -> None:
    registry = build_registry()
    for name, domain in (
        ("send_chat_message", "chats"),
        ("create_list_item", "sharepoint_sites"),
        ("create_contact", "contacts"),
        ("create_planner_task", "planner"),
        ("create_todo_task", "todo"),
    ):
        tool = registry.get(name)
        assert tool is not None, name
        assert tool.read_only is False, name
        assert tool.requires_confirmation is True, name
        assert tool.domain == domain, name


def test_read_only_domains_have_no_write_tools() -> None:
    registry = build_registry()
    for domain in ("onenote", "usage_reports", "service_health"):
        tools = registry.tools_for_domain(domain)
        assert tools, domain
        assert all(tool.read_only for tool in tools), domain


# --- mock client routing (one representative read per domain) --------------


@pytest.mark.asyncio
async def test_mock_routes_one_read_per_domain() -> None:
    client = MockGraphClient()
    cases = [
        ("/users/user-ada/chats", "value"),
        ("/sites", "value"),
        ("/users/user-ada/onenote/notebooks", "value"),
        ("/users/user-ada/contacts", "value"),
        ("/groups/group-finance/planner/plans", "value"),
        ("/users/user-ada/todo/lists", "value"),
        ("/reports/getTeamsUserActivityCounts(period='D7')", "value"),
        ("/admin/serviceAnnouncement/healthOverviews", "value"),
    ]
    for endpoint, key in cases:
        result = await client.request("GET", endpoint)
        assert isinstance(result, dict) and result.get(key), endpoint


@pytest.mark.asyncio
async def test_user_get_by_id_still_works() -> None:
    # The new /users/{id}/... routes must not shadow the plain get-by-id route.
    client = MockGraphClient()
    user = await client.request("GET", "/users/user-ada")
    assert user["displayName"] == "Ada Lovelace"


# --- executor: reads run, writes are gated ---------------------------------


@pytest.mark.asyncio
async def test_list_sites_runs_through_executor() -> None:
    record = await build_executor().execute_call(LLMToolCall(id="1", name="list_sites", args={}))
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_send_chat_message_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="send_chat_message", args={"chat_id": "chat-1", "content": "hi"})
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_send_chat_message_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="send_chat_message",
            args={
                "chat_id": "chat-1",
                "content": "Standup at 10am.",
                "confirmed": True,
                "reason": "Posting the standup reminder the user asked for.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True
