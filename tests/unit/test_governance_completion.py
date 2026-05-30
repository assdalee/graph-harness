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


def test_governance_completion_domains_registered() -> None:
    domains = {domain.name for domain in build_registry().list_domains()}
    assert {
        "lifecycle_workflows",
        "administrative_units",
        "b2b_collaboration",
    } <= domains


def test_governance_completion_write_tools_have_expected_flags() -> None:
    registry = build_registry()

    activate = registry.get("activate_workflow")
    add_member = registry.get("add_administrative_unit_member")
    invite = registry.get("invite_guest_user")

    assert activate is not None
    assert activate.read_only is False and activate.requires_confirmation is True
    assert activate.domain == "lifecycle_workflows"
    assert activate.safety == "mutation"

    assert add_member is not None
    assert add_member.read_only is False and add_member.requires_confirmation is True
    assert add_member.domain == "administrative_units"
    assert add_member.safety == "mutation"

    assert invite is not None
    assert invite.read_only is False and invite.requires_confirmation is True
    assert invite.domain == "b2b_collaboration"
    assert invite.safety == "mutation"


def test_governance_completion_read_tools_are_read_only() -> None:
    registry = build_registry()
    for name in (
        "list_lifecycle_workflows",
        "list_workflow_runs",
        "list_administrative_units",
        "list_administrative_unit_members",
        "list_guest_users",
    ):
        tool = registry.get(name)
        assert tool is not None and tool.read_only is True


# --- mock client routing ---------------------------------------------------


@pytest.mark.asyncio
async def test_mock_routes_governance_completion_reads() -> None:
    client = MockGraphClient()
    assert (await client.request("GET", "/identityGovernance/lifecycleWorkflows/workflows"))[
        "value"
    ]
    assert (
        await client.request(
            "GET", "/identityGovernance/lifecycleWorkflows/workflows/wf-onboard/runs"
        )
    )["value"]
    assert (await client.request("GET", "/directory/administrativeUnits"))["value"]
    assert (await client.request("GET", "/directory/administrativeUnits/au-emea/members"))["value"]
    guests = await client.request("GET", "/users", params={"$filter": "userType eq 'Guest'"})
    assert isinstance(guests["value"], list)


# --- executor: reads run, writes are gated ---------------------------------


@pytest.mark.asyncio
async def test_list_lifecycle_workflows_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="list_lifecycle_workflows", args={})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_list_guest_users_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="list_guest_users", args={})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_activate_workflow_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="activate_workflow",
            args={"workflow_id": "wf-onboard", "subject_ids": ["user-ada"]},
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_activate_workflow_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="activate_workflow",
            args={
                "workflow_id": "wf-onboard",
                "subject_ids": ["user-ada"],
                "confirmed": True,
                "reason": "Manual onboarding run approved by HR.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_add_administrative_unit_member_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="add_administrative_unit_member",
            args={"au_id": "au-emea", "member_id": "user-ada"},
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_add_administrative_unit_member_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="add_administrative_unit_member",
            args={
                "au_id": "au-emea",
                "member_id": "user-ada",
                "confirmed": True,
                "reason": "Scoping admin to EMEA per approved request.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_invite_guest_user_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="invite_guest_user",
            args={"email": "partner@external.example"},
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_invite_guest_user_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="invite_guest_user",
            args={
                "email": "partner@external.example",
                "confirmed": True,
                "reason": "Approved external collaboration for project Apollo.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True
