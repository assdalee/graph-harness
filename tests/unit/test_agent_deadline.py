import pytest

from graph_harness.core.config import Settings
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.fake_client import FakeLLMClient
from graph_harness.agent.agent import GraphAgent
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import GraphToolFactory


def _agent(**overrides) -> GraphAgent:
    settings = Settings(graph_backend="mock", llm_backend="fake", **overrides)
    registry = GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()
    executor = ToolExecutor(registry, settings)
    return GraphAgent(
        llm_client=FakeLLMClient(settings),
        registry=registry,
        executor=executor,
        settings=settings,
    )


@pytest.mark.asyncio
async def test_zero_budget_disables_deadline() -> None:
    agent = _agent(agent_max_wall_clock_seconds=0)
    response = await agent.run(messages=[{"role": "user", "content": "List users"}])
    assert response.status_code if hasattr(response, "status_code") else True
    assert response.stop_reason != "deadline_exceeded"


@pytest.mark.asyncio
async def test_expired_budget_finalizes_early(monkeypatch) -> None:
    agent = _agent(agent_max_wall_clock_seconds=600)

    # First monotonic() call computes the deadline; subsequent calls land past it.
    calls = {"n": 0}

    def fake_monotonic() -> float:
        calls["n"] += 1
        return 0.0 if calls["n"] == 1 else 10_000.0

    monkeypatch.setattr("graph_harness.agent.agent.time.monotonic", fake_monotonic)
    response = await agent.run(messages=[{"role": "user", "content": "List users"}])

    assert response.stop_reason == "deadline_exceeded"
    assert any("budget" in w for w in response.warnings)
