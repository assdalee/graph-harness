import pytest

from graph_harness.core.config import Settings
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.types import LLMToolCall
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import GraphToolFactory

TIER3_DOMAINS = {
    "universal_print",
    "education",
    "cloud_pc",
    "viva",
    "places",
    "change_notifications",
}


def build_registry():
    return GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()


def build_executor():
    return ToolExecutor(build_registry(), Settings(llm_model="openai/gpt-4o-mini"))


# --- registry / domains ----------------------------------------------------


def test_tier3_domains_registered() -> None:
    domains = {domain.name for domain in build_registry().list_domains()}
    assert TIER3_DOMAINS <= domains


def test_write_tools_are_gated() -> None:
    registry = build_registry()
    for name, domain, safety in (
        ("cancel_print_job", "universal_print", "mutation"),
        ("reboot_cloud_pc", "cloud_pc", "mutation"),
        ("reprovision_cloud_pc", "cloud_pc", "destructive"),
        ("create_subscription", "change_notifications", "mutation"),
        ("renew_subscription", "change_notifications", "mutation"),
        ("delete_subscription", "change_notifications", "destructive"),
    ):
        tool = registry.get(name)
        assert tool is not None, name
        assert tool.read_only is False, name
        assert tool.requires_confirmation is True, name
        assert tool.safety == safety, name
        assert tool.domain == domain, name


def test_read_only_domains_have_no_write_tools() -> None:
    registry = build_registry()
    for domain in ("education", "viva", "places"):
        tools = registry.tools_for_domain(domain)
        assert tools, domain
        assert all(tool.read_only for tool in tools), domain


# --- mock client routing (one representative read per domain) --------------


@pytest.mark.asyncio
async def test_mock_routes_one_read_per_domain() -> None:
    client = MockGraphClient()
    cases = [
        ("/print/printers", "value"),
        ("/education/schools", "value"),
        ("/deviceManagement/virtualEndpoint/cloudPCs", "value"),
        ("/employeeExperience/communities", "value"),
        ("/places/microsoft.graph.room", "value"),
        ("/subscriptions", "value"),
    ]
    for endpoint, key in cases:
        result = await client.request("GET", endpoint)
        assert isinstance(result, dict) and result.get(key), endpoint


@pytest.mark.asyncio
async def test_get_by_id_and_subresource_routes() -> None:
    client = MockGraphClient()
    printer = await client.request("GET", "/print/printers/printer-1")
    assert printer["displayName"] == "Main office printer"
    jobs = await client.request("GET", "/print/printers/printer-1/jobs")
    assert jobs["value"][0]["documentName"] == "Report.pdf"
    members = await client.request("GET", "/education/classes/class-1/members")
    assert members["value"][0]["displayName"] == "Sam Student"
    cpc = await client.request("GET", "/deviceManagement/virtualEndpoint/cloudPCs/cpc-1")
    assert cpc["displayName"] == "ADA-CPC"


# --- executor: reads run, writes are gated ---------------------------------


@pytest.mark.asyncio
async def test_list_cloud_pcs_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="list_cloud_pcs", args={})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_list_places_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="list_places", args={})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_reprovision_cloud_pc_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="reprovision_cloud_pc", args={"cloud_pc_id": "cpc-1"})
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_reprovision_cloud_pc_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="reprovision_cloud_pc",
            args={
                "cloud_pc_id": "cpc-1",
                "confirmed": True,
                "reason": "User explicitly requested reprovisioning to reset the device.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_create_subscription_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="create_subscription",
            args={
                "change_type": "created,updated",
                "notification_url": "https://example.com/webhook",
                "resource": "me/mailFolders/Inbox/messages",
                "expiration_date_time": "2026-06-01T00:00:00Z",
            },
        )
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_delete_subscription_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="delete_subscription",
            args={
                "subscription_id": "sub-1",
                "confirmed": True,
                "reason": "User asked to tear down the obsolete webhook.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True
