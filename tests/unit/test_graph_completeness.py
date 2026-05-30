import pytest

from graph_harness.core.config import Settings
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.types import LLMToolCall
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import (
    GetSecurityAlertArgs,
    GetSecurityIncidentArgs,
    GraphToolFactory,
    ListGroupMembersArgs,
    UpdateSecurityAlertArgs,
)


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def request(self, method, endpoint, **kwargs):
        self.calls.append({"method": method, "endpoint": endpoint, **kwargs})
        return {"id": "x"}

    async def request_collection(self, endpoint, **kwargs):
        self.calls.append({"method": "GET", "endpoint": endpoint, **kwargs})
        return {"value": []}


def _factory_recording() -> tuple[GraphToolFactory, _RecordingClient]:
    client = _RecordingClient()
    return GraphToolFactory(client, GraphOperationCatalog.default()), client


def _executor() -> ToolExecutor:
    registry = GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()
    return ToolExecutor(registry, Settings(graph_backend="mock", llm_backend="fake"))


# --- group member pagination -------------------------------------------


@pytest.mark.asyncio
async def test_list_group_members_paginates() -> None:
    factory, client = _factory_recording()
    await factory.list_group_members(
        ListGroupMembersArgs(group_id="g1", all_pages=True, max_pages=3)
    )
    call = client.calls[-1]
    assert call["method"] == "GET"
    assert call["endpoint"] == "/groups/g1/members"
    assert call["all_pages"] is True
    assert call["max_pages"] == 3


# --- security get-by-id + triage ---------------------------------------


def test_security_domain_registers_new_tools() -> None:
    registry = GraphToolFactory(
        MockGraphClient(), GraphOperationCatalog.default()
    ).build_registry()
    names = {tool.name for tool in registry.tools_for_domain("security")}
    assert {
        "list_security_alerts",
        "get_security_alert",
        "update_security_alert",
        "list_security_incidents",
        "get_security_incident",
        "update_security_incident",
        "run_hunting_query",
        "create_threat_assessment_request",
    } == names
    update = registry.get("update_security_alert")
    assert update.read_only is False
    assert update.requires_confirmation is True


@pytest.mark.asyncio
async def test_get_security_alert_endpoint() -> None:
    factory, client = _factory_recording()
    await factory.get_security_alert(GetSecurityAlertArgs(alert_id="a1"))
    assert client.calls[-1]["endpoint"] == "/security/alerts_v2/a1"


@pytest.mark.asyncio
async def test_get_security_incident_endpoint() -> None:
    factory, client = _factory_recording()
    await factory.get_security_incident(GetSecurityIncidentArgs(incident_id="i1"))
    assert client.calls[-1]["endpoint"] == "/security/incidents/i1"


@pytest.mark.asyncio
async def test_update_security_alert_builds_patch_body() -> None:
    factory, client = _factory_recording()
    await factory.update_security_alert(
        UpdateSecurityAlertArgs(
            alert_id="a1", confirmed=True, reason="triage", status="resolved", assigned_to="me"
        )
    )
    call = client.calls[-1]
    assert call["method"] == "PATCH"
    assert call["endpoint"] == "/security/alerts_v2/a1"
    assert call["json_data"] == {"status": "resolved", "assignedTo": "me"}


@pytest.mark.asyncio
async def test_update_security_alert_requires_confirmation() -> None:
    executor = _executor()
    record = await executor.execute_call(
        LLMToolCall(id="c1", name="update_security_alert", args={"alert_id": "a1", "status": "resolved"})
    )
    assert record.error is not None
    assert record.error.code == "confirmation_required"


@pytest.mark.asyncio
async def test_update_security_alert_rejects_empty_update() -> None:
    factory, _client = _factory_recording()
    result = await factory.update_security_alert(
        UpdateSecurityAlertArgs(alert_id="a1", confirmed=True, reason="noop")
    )
    assert result.ok is False
    assert result.error.code == "validation_error"
