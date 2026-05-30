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


def test_governance_depth_domains_registered() -> None:
    domains = {domain.name for domain in build_registry().list_domains()}
    assert {
        "privileged_identity",
        "access_reviews",
        "authentication_methods",
        "identity_protection",
    } <= domains


def test_governance_depth_write_tools_have_expected_flags() -> None:
    registry = build_registry()

    create_elig = registry.get("create_role_eligibility_request")
    activate = registry.get("activate_eligible_role")
    stop_review = registry.get("stop_access_review_instance")
    delete_method = registry.get("delete_user_authentication_method")
    reset_pw = registry.get("reset_password")
    dismiss = registry.get("dismiss_risky_users")
    confirm = registry.get("confirm_compromised_users")

    assert create_elig is not None
    assert create_elig.read_only is False and create_elig.requires_confirmation is True
    assert create_elig.domain == "privileged_identity"

    assert activate is not None and activate.requires_confirmation is True
    assert activate.domain == "privileged_identity"

    assert stop_review is not None
    assert stop_review.read_only is False and stop_review.requires_confirmation is True
    assert stop_review.domain == "access_reviews"

    assert delete_method is not None and delete_method.safety == "security_mutation"
    assert delete_method.domain == "authentication_methods"
    assert reset_pw is not None and reset_pw.safety == "security_mutation"

    assert dismiss is not None
    assert dismiss.read_only is False and dismiss.requires_confirmation is True
    assert dismiss.domain == "identity_protection"
    assert confirm is not None and confirm.safety == "security_mutation"


def test_governance_depth_read_tools_are_read_only() -> None:
    registry = build_registry()
    for name in (
        "list_eligible_role_assignments",
        "list_active_role_assignment_schedules",
        "list_access_review_definitions",
        "list_access_packages",
        "list_user_authentication_methods",
        "list_risky_users",
        "list_risk_detections",
    ):
        tool = registry.get(name)
        assert tool is not None and tool.read_only is True


# --- mock client routing ---------------------------------------------------


@pytest.mark.asyncio
async def test_mock_routes_governance_depth_reads() -> None:
    client = MockGraphClient()
    assert (
        await client.request("GET", "/roleManagement/directory/roleEligibilityScheduleInstances")
    )["value"]
    assert (
        await client.request("GET", "/roleManagement/directory/roleAssignmentScheduleInstances")
    )["value"]
    assert (await client.request("GET", "/identityGovernance/accessReviews/definitions"))["value"]
    assert (
        await client.request("GET", "/identityGovernance/entitlementManagement/accessPackages")
    )["value"]
    assert (await client.request("GET", "/identityProtection/riskyUsers"))["value"]
    assert (await client.request("GET", "/identityProtection/riskDetections"))["value"]
    assert (await client.request("GET", "/users/user-ada/authentication/methods"))["value"]


# --- executor: reads run, writes are gated ---------------------------------


@pytest.mark.asyncio
async def test_list_risky_users_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="list_risky_users", args={})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_dismiss_risky_users_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="dismiss_risky_users",
            args={"user_ids": ["user-ada"]},
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_dismiss_risky_users_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="dismiss_risky_users",
            args={
                "user_ids": ["user-ada"],
                "confirmed": True,
                "reason": "Investigated sign-in; risk is a false positive.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_create_role_eligibility_request_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="create_role_eligibility_request",
            args={
                "principal_id": "user-ada",
                "role_definition_id": "def-ga",
                "justification": "Temporary admin access for migration.",
            },
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_create_role_eligibility_request_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="create_role_eligibility_request",
            args={
                "principal_id": "user-ada",
                "role_definition_id": "def-ga",
                "justification": "Temporary admin access for migration.",
                "confirmed": True,
                "reason": "Approved by change board for migration window.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True
