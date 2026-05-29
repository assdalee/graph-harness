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


def test_device_management_domain_registered() -> None:
    domains = {domain.name for domain in build_registry().list_domains()}
    assert "device_management" in domains


def test_device_management_write_tools_have_expected_safety_flags() -> None:
    registry = build_registry()

    wipe = registry.get("wipe_managed_device")
    retire = registry.get("retire_managed_device")
    sync = registry.get("sync_managed_device")
    list_devices = registry.get("list_managed_devices")

    assert wipe is not None
    assert wipe.read_only is False and wipe.requires_confirmation is True
    assert wipe.domain == "device_management" and wipe.safety == "destructive"

    assert retire is not None
    assert retire.read_only is False and retire.requires_confirmation is True
    assert retire.domain == "device_management" and retire.safety == "destructive"

    assert sync is not None
    assert sync.read_only is False and sync.requires_confirmation is True
    assert sync.domain == "device_management" and sync.safety == "mutation"

    assert list_devices is not None and list_devices.read_only is True


# --- mock client routing ---------------------------------------------------


@pytest.mark.asyncio
async def test_mock_routes_device_management_reads() -> None:
    client = MockGraphClient()
    assert (await client.request("GET", "/deviceManagement/managedDevices"))["value"]
    assert (await client.request("GET", "/deviceManagement/deviceCompliancePolicies"))["value"]
    assert (await client.request("GET", "/deviceManagement/deviceConfigurations"))["value"]


@pytest.mark.asyncio
async def test_mock_managed_device_get_by_id() -> None:
    client = MockGraphClient()
    device = await client.request("GET", "/deviceManagement/managedDevices/md-laptop")
    assert device["deviceName"] == "ADA-LAPTOP"

    missing = await client.request("GET", "/deviceManagement/managedDevices/nope")
    assert "error" in missing and missing["error"]["status_code"] == 404


# --- executor: reads run, writes are gated ---------------------------------


@pytest.mark.asyncio
async def test_list_managed_devices_runs_through_executor() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="list_managed_devices", args={})
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_wipe_managed_device_requires_confirmation() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(id="1", name="wipe_managed_device", args={"device_id": "md-laptop"})
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_wipe_managed_device_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="wipe_managed_device",
            args={
                "device_id": "md-laptop",
                "confirmed": True,
                "reason": "Lost device reported by employee.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True


@pytest.mark.asyncio
async def test_retire_managed_device_executes_when_confirmed() -> None:
    record = await build_executor().execute_call(
        LLMToolCall(
            id="1",
            name="retire_managed_device",
            args={
                "device_id": "md-phone",
                "confirmed": True,
                "reason": "Offboarding departed employee.",
            },
        )
    )
    assert record.error is None
    assert record.result is not None and record.result.ok is True
