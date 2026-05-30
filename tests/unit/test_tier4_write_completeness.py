import pytest

from graph_harness.core.config import Settings
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.types import LLMToolCall
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import GraphToolFactory

# (tool_name, domain, safety) for every write tool added in Tier 4.
NEW_WRITES = [
    ("create_user", "identity_access", "mutation"),
    ("create_group", "identity_access", "mutation"),
    ("update_group", "identity_access", "mutation"),
    ("delete_group", "identity_access", "destructive"),
    ("add_group_owner", "identity_access", "mutation"),
    ("remove_group_owner", "identity_access", "mutation"),
    ("set_service_principal_enabled", "identity_access", "security_mutation"),
    ("update_security_incident", "security", "security_mutation"),
    ("create_threat_assessment_request", "security", "mutation"),
    ("create_conditional_access_policy", "conditional_access", "security_mutation"),
    ("delete_conditional_access_policy", "conditional_access", "destructive"),
    ("remove_user_license", "license_management", "mutation"),
    ("add_application_password", "applications", "security_mutation"),
    ("remove_application_password", "applications", "security_mutation"),
    ("reply_message", "mail", "mutation"),
    ("forward_message", "mail", "mutation"),
    ("move_message", "mail", "mutation"),
    ("update_message", "mail", "mutation"),
    ("delete_message", "mail", "destructive"),
    ("create_mail_folder", "mail", "mutation"),
    ("update_event", "calendar", "mutation"),
    ("respond_to_event", "calendar", "mutation"),
    ("create_team", "teams", "mutation"),
    ("add_team_member", "teams", "mutation"),
    ("create_channel", "teams", "mutation"),
    ("archive_team", "teams", "mutation"),
    ("create_chat", "chats", "mutation"),
    ("upload_file", "files", "mutation"),
    ("create_folder", "files", "mutation"),
    ("delete_drive_item", "files", "destructive"),
    ("copy_drive_item", "files", "mutation"),
    ("remote_lock_device", "device_management", "mutation"),
    ("reset_device_passcode", "device_management", "security_mutation"),
    ("restart_managed_device", "device_management", "mutation"),
    ("update_list_item", "sharepoint_sites", "mutation"),
    ("delete_list_item", "sharepoint_sites", "destructive"),
    ("update_contact", "contacts", "mutation"),
    ("delete_contact", "contacts", "destructive"),
    ("update_planner_task", "planner", "mutation"),
    ("delete_planner_task", "planner", "destructive"),
    ("update_todo_task", "todo", "mutation"),
    ("delete_todo_task", "todo", "destructive"),
    ("cancel_booking_appointment", "bookings", "mutation"),
]


def build_registry():
    return GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()


def build_executor():
    return ToolExecutor(build_registry(), Settings(llm_model="openai/gpt-4o-mini"))


# --- flags / safety --------------------------------------------------------


def test_all_new_writes_are_gated_with_expected_safety() -> None:
    registry = build_registry()
    for name, domain, safety in NEW_WRITES:
        tool = registry.get(name)
        assert tool is not None, name
        assert tool.read_only is False, name
        assert tool.requires_confirmation is True, name
        assert tool.domain == domain, name
        assert tool.safety == safety, name


def test_run_hunting_query_is_read_only() -> None:
    tool = build_registry().get("run_hunting_query")
    assert tool is not None
    assert tool.read_only is True
    assert tool.requires_confirmation is False
    assert tool.domain == "security"


# --- executor: confirmation gating ----------------------------------------


@pytest.mark.asyncio
async def test_create_user_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="create_user",
            args={
                "user_principal_name": "newbie@example.com",
                "display_name": "New Bie",
                "mail_nickname": "newbie",
                "password": "Sup3rSecret!",
            },
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_create_user_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="create_user",
            args={
                "user_principal_name": "newbie@example.com",
                "display_name": "New Bie",
                "mail_nickname": "newbie",
                "password": "Sup3rSecret!",
                "confirmed": True,
                "reason": "Provisioning the account the admin requested.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_delete_drive_item_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="delete_drive_item",
            args={"drive_id": "drive-1", "item_id": "item-budget"},
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


# --- executor: reads / PUT upload run through the mock ---------------------


@pytest.mark.asyncio
async def test_run_hunting_query_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="run_hunting_query",
            args={"query": "DeviceProcessEvents | take 10"},
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_upload_file_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="upload_file",
            args={
                "drive_id": "drive-1",
                "file_name": "notes.txt",
                "content": "hello world",
                "confirmed": True,
                "reason": "Uploading the file the user provided.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


# --- selection: resolvers survive even as identity_access grew -------------


def test_group_workflow_still_keeps_resolvers() -> None:
    registry = build_registry()
    selected = registry.select_tools_for_query("Add Sarah to the Finance group", max_tools=16)
    names = {tool.name for tool in selected}
    assert "resolve_user" in names
    assert "resolve_group" in names
    assert "add_group_member" in names
