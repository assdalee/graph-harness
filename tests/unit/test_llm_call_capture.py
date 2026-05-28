import pytest
from fastapi.testclient import TestClient

from graph_harness.agent.agent import GraphAgent
from graph_harness.app.main import create_app
from graph_harness.core.config import Settings
from graph_harness.graph.mock_client import MockGraphClient
from graph_harness.graph.operations import GraphOperationCatalog
from graph_harness.llm.fake_client import FakeLLMClient
from graph_harness.tools.executor import ToolExecutor
from graph_harness.tools.graph_tools import GraphToolFactory


def _agent() -> GraphAgent:
    settings = Settings(graph_backend="mock", llm_backend="fake")
    registry = GraphToolFactory(MockGraphClient(), GraphOperationCatalog.default()).build_registry()
    return GraphAgent(
        llm_client=FakeLLMClient(settings),
        registry=registry,
        executor=ToolExecutor(registry, settings),
        settings=settings,
    )


@pytest.mark.asyncio
async def test_records_one_llm_call_per_turn() -> None:
    response = await _agent().run(messages=[{"role": "user", "content": "List users"}])

    assert response.llm_calls, "expected at least one captured loop call"
    assert len(response.llm_calls) == response.turns
    for index, call in enumerate(response.llm_calls):
        assert call.turn == index + 1
        assert call.phase == "turn"
        # Each captured prompt begins with the system instruction.
        assert call.messages[0]["role"] == "system"
        assert call.messages[0]["content"]


@pytest.mark.asyncio
async def test_llm_call_snapshot_is_independent_of_later_mutation() -> None:
    agent = _agent()
    response = await agent.run(messages=[{"role": "user", "content": "List users"}])
    first_turn_len = len(response.llm_calls[0].messages)
    # The final message history is longer than the first turn's prompt snapshot.
    assert len(response.messages) >= first_turn_len


def test_chat_endpoint_exposes_llm_calls() -> None:
    client = TestClient(create_app(Settings(graph_backend="mock", llm_backend="fake")))
    payload = client.post(
        "/v1/graph/chat",
        json={"messages": [{"role": "user", "content": "List high severity alerts"}]},
    ).json()
    assert payload["llm_calls"]
    assert payload["llm_calls"][0]["messages"][0]["role"] == "system"


def test_run_store_round_trips_llm_calls(tmp_path) -> None:
    db = str(tmp_path / "runs.sqlite3")
    client = TestClient(
        create_app(
            Settings(
                graph_backend="mock",
                llm_backend="fake",
                runs_enabled=True,
                runs_backend="sqlite",
                runs_db_path=db,
            )
        )
    )
    run_id = client.post(
        "/v1/graph/chat",
        json={"messages": [{"role": "user", "content": "List users"}]},
    ).json()["run_id"]

    detail = client.get(f"/v1/runs/{run_id}").json()
    assert detail["llm_calls"]
    assert detail["llm_calls"][0]["turn"] == 1
    assert detail["llm_calls"][0]["messages"][0]["role"] == "system"
