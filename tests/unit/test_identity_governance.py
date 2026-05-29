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


def test_governance_domains_registered() -> None:
    domains = {domain.name for domain in build_registry().list_domains()}
    assert {
        "role_management",
        "conditional_access",
        "license_management",
        "applications",
    } <= domains


def test_new_tools_have_expected_safety_flags() -> None:
    registry = build_registry()

    list_roles = registry.get("list_directory_roles")
    assign_role = registry.get("assign_directory_role")
    delete_app = registry.get("delete_application")
    set_ca = registry.get("set_conditional_access_policy_state")

    assert list_roles is not None and list_roles.read_only is True
    assert assign_role is not None
    assert assign_role.read_only is False and assign_role.requires_confirmation is True
    assert assign_role.domain == "role_management"
    assert delete_app is not None and delete_app.safety == "destructive"
    assert set_ca is not None and set_ca.requires_confirmation is True


# --- mock client routing ---------------------------------------------------


@pytest.mark.asyncio
async def test_mock_routes_governance_reads() -> None:
    client = MockGraphClient()
    assert (await client.request("GET", "/directoryRoles"))["value"]
    assert (await client.request("GET", "/roleManagement/directory/roleDefinitions"))["value"]
    assert (await client.request("GET", "/roleManagement/directory/roleAssignments"))["value"]
    assert (await client.request("GET", "/identity/conditionalAccess/policies"))["value"]
    assert (await client.request("GET", "/subscribedSkus"))["value"]
    assert (await client.request("GET", "/users/user-ada/licenseDetails"))["value"]
    assert (await client.request("GET", "/applications"))["value"]


@pytest.mark.asyncio
async def test_mock_get_by_id_and_missing() -> None:
    client = MockGraphClient()
    policy = await client.request("GET", "/identity/conditionalAccess/policies/ca-1")
    assert policy["displayName"] == "Require MFA for admins"
    missing = await client.request("GET", "/applications/nope")
    assert missing["error"]["status_code"] == 404


# --- executor: reads run, writes are gated ---------------------------------


@pytest.mark.asyncio
async def test_list_directory_roles_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="list_directory_roles", args={})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_assign_directory_role_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="assign_directory_role",
            args={"principal_id": "user-ada", "role_definition_id": "def-ga"},
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_assign_directory_role_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="assign_directory_role",
            args={
                "principal_id": "user-ada",
                "role_definition_id": "def-ga",
                "confirmed": True,
                "reason": "Break-glass GA grant for incident response.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_assign_user_license_requires_a_sku() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="assign_user_license",
            args={"user_id": "user-ada", "confirmed": True, "reason": "license cleanup"},
        )
    )
    assert record.error is not None
    assert record.error.code == "validation_error"
