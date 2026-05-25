import pytest

from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.tools.graph_tools import GetDeviceArgs, GraphToolFactory


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def request(self, method, endpoint, **kwargs):
        self.calls.append({"method": method, "endpoint": endpoint, **kwargs})
        return {"id": "device-1"}

    async def request_collection(self, endpoint, **kwargs):
        self.calls.append({"method": "GET", "endpoint": endpoint, **kwargs})
        return {"value": []}


def _registry():
    return GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()


def test_devices_domain_drops_misleading_intune_tags() -> None:
    registry = _registry()
    devices = next(d for d in registry.list_domains() if d.name == "devices")
    assert "intune" not in devices.tags
    assert "compliance" not in devices.tags
    assert "intune" not in devices.description.lower() or "does not include" in devices.description.lower()


def test_devices_domain_registers_get_device() -> None:
    registry = _registry()
    names = {tool.name for tool in registry.tools_for_domain("devices")}
    assert {"list_devices", "get_device"} <= names
    get_device = registry.get("get_device")
    assert get_device.read_only is True


@pytest.mark.asyncio
async def test_get_device_hits_correct_endpoint() -> None:
    client = _RecordingClient()
    factory = GraphToolFactory(client, GraphOperationCatalog.default())
    await factory.get_device(GetDeviceArgs(device_id="device-1"))
    assert client.calls[-1]["method"] == "GET"
    assert client.calls[-1]["endpoint"] == "/devices/device-1"
