import pytest

from graph_harness.core.config import Settings
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.types import LLMToolCall
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import GraphToolFactory


def build_registry():
    return GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()


def build_executor():
    return ToolExecutor(build_registry(), Settings(llm_model="openai/gpt-4o-mini"))


# --- registry / domains ----------------------------------------------------


def test_m365_domains_registered() -> None:
    domains = {domain.name for domain in build_registry().list_domains()}
    assert {"mail", "calendar", "teams", "files"} <= domains


def test_m365_write_tools_have_expected_safety_flags() -> None:
    registry = build_registry()

    send_mail = registry.get("send_mail")
    create_event = registry.get("create_event")
    send_channel_message = registry.get("send_channel_message")
    list_messages = registry.get("list_messages")

    assert send_mail is not None
    assert send_mail.read_only is False and send_mail.requires_confirmation is True
    assert send_mail.domain == "mail" and send_mail.safety == "mutation"

    assert create_event is not None
    assert create_event.read_only is False and create_event.requires_confirmation is True
    assert create_event.domain == "calendar" and create_event.safety == "mutation"

    assert send_channel_message is not None
    assert send_channel_message.read_only is False
    assert send_channel_message.requires_confirmation is True
    assert send_channel_message.domain == "teams" and send_channel_message.safety == "mutation"

    assert list_messages is not None and list_messages.read_only is True


# --- mock client routing ---------------------------------------------------


@pytest.mark.asyncio
async def test_mock_routes_m365_reads() -> None:
    client = MockGraphClient()
    assert (await client.request("GET", "/users/user-ada/messages"))["value"]
    assert (await client.request("GET", "/users/user-ada/mailFolders"))["value"]
    assert (await client.request("GET", "/users/user-ada/events"))["value"]
    assert (await client.request("GET", "/users/user-ada/joinedTeams"))["value"]
    assert (await client.request("GET", "/users/user-ada/drive/root/children"))["value"]
    assert (await client.request("GET", "/users/user-ada/drive/root/search(q='budget')"))["value"]
    assert (await client.request("GET", "/teams/team-eng/channels"))["value"]
    assert (await client.request("GET", "/teams/team-eng/channels/channel-general/messages"))[
        "value"
    ]


@pytest.mark.asyncio
async def test_mock_m365_get_by_id() -> None:
    client = MockGraphClient()
    message = await client.request("GET", "/users/user-ada/messages/msg-1")
    assert message["subject"] == "Q2 planning"
    event = await client.request("GET", "/users/user-ada/events/event-1")
    assert event["subject"] == "Sprint review"
    item = await client.request("GET", "/users/user-ada/drive/items/item-budget")
    assert item["name"] == "Budget.xlsx"


# --- executor: reads run, writes are gated ---------------------------------


@pytest.mark.asyncio
async def test_list_messages_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="list_messages", args={"user_id": "user-ada"})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_send_mail_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="send_mail",
            args={
                "user_id": "user-ada",
                "subject": "Hello",
                "body": "Hi there",
                "to_recipients": ["sarah@example.com"],
            },
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_send_mail_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="send_mail",
            args={
                "user_id": "user-ada",
                "subject": "Hello",
                "body": "Hi there",
                "to_recipients": ["sarah@example.com"],
                "confirmed": True,
                "reason": "Sending requested follow-up email.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_send_channel_message_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="send_channel_message",
            args={
                "team_id": "team-eng",
                "channel_id": "channel-general",
                "content": "Deploy complete.",
            },
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_create_event_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="create_event",
            args={
                "user_id": "user-ada",
                "subject": "Planning",
                "start_datetime": "2026-06-10T09:00:00",
                "end_datetime": "2026-06-10T10:00:00",
                "confirmed": True,
                "reason": "Scheduling requested planning meeting.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True
