import os
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from graph_harness.api_models.chat import AgentTraceEvent, ToolCallRecord
from graph_harness.app.main import create_app
from graph_harness.core.config import Settings
from graph_harness.runs.sqlite_store import SqliteRunStore
from graph_harness.runs.store import RunListFilters, RunRecord


def _record(**overrides) -> RunRecord:
    now = datetime.now(timezone.utc)
    defaults: dict = {
        "id": "run-1",
        "thread_id": "thread-1",
        "user_id": "alice",
        "created_at": now,
        "finished_at": now,
        "duration_ms": 42,
        "input_message": "List users",
        "llm_model": "openai/gpt-4o-mini",
        "llm_backend": "fake",
        "status": "completed",
        "stop_reason": "final_answer",
        "turns": 1,
        "answer": "Done.",
        "warnings": ["w1"],
        "data": [{"a": 1}],
        "messages": [{"role": "user", "content": "hi"}],
        "tool_calls": [
            ToolCallRecord(id="call-1", name="list_users", args={"top": 5}, read_only=True),
        ],
        "trace_events": [
            AgentTraceEvent(event="run_started", turn=0, message="", metadata={"k": "v"}),
        ],
        "config_snapshot": {"llm_model": "openai/gpt-4o-mini"},
        "tags": {"eval_set": "mock", "scenario_id": "list_users"},
    }
    defaults.update(overrides)
    return RunRecord(**defaults)


@pytest.mark.asyncio
async def test_sqlite_store_round_trip(tmp_path) -> None:
    store = SqliteRunStore(str(tmp_path / "runs.sqlite3"))
    record = _record()

    await store.record(record)

    loaded = await store.get("run-1")
    assert loaded is not None
    assert loaded.id == "run-1"
    assert loaded.status == "completed"
    assert loaded.warnings == ["w1"]
    assert loaded.tags == {"eval_set": "mock", "scenario_id": "list_users"}
    assert len(loaded.tool_calls) == 1
    assert loaded.tool_calls[0].name == "list_users"
    assert loaded.tool_calls[0].args == {"top": 5}
    assert len(loaded.trace_events) == 1
    assert loaded.trace_events[0].event == "run_started"
    assert loaded.trace_events[0].metadata == {"k": "v"}


@pytest.mark.asyncio
async def test_sqlite_store_list_and_filters(tmp_path) -> None:
    store = SqliteRunStore(str(tmp_path / "runs.sqlite3"))
    await store.record(_record(id="a", status="completed"))
    await store.record(_record(id="b", status="failed", thread_id="thread-2"))
    await store.record(_record(id="c", status="completed", user_id="bob"))

    all_runs = await store.list(RunListFilters())
    assert {run.id for run in all_runs} == {"a", "b", "c"}
    assert await store.count(RunListFilters()) == 3

    only_completed = await store.list(RunListFilters(status="completed"))
    assert {run.id for run in only_completed} == {"a", "c"}

    by_thread = await store.list(RunListFilters(thread_id="thread-2"))
    assert [run.id for run in by_thread] == ["b"]

    by_user = await store.list(RunListFilters(user_id="bob"))
    assert [run.id for run in by_user] == ["c"]

    by_tag = await store.list(RunListFilters(tag_key="eval_set", tag_value="mock"))
    assert len(by_tag) == 3


@pytest.mark.asyncio
async def test_sqlite_store_overwrites_on_replay(tmp_path) -> None:
    store = SqliteRunStore(str(tmp_path / "runs.sqlite3"))
    await store.record(_record(id="dup", answer="first"))
    await store.record(_record(id="dup", answer="second"))

    loaded = await store.get("dup")
    assert loaded is not None
    assert loaded.answer == "second"


def _client_with_store(tmp_path, **overrides) -> TestClient:
    db_path = str(tmp_path / "runs.sqlite3")
    settings = Settings(
        graph_backend="mock",
        llm_backend="fake",
        runs_enabled=True,
        runs_backend="sqlite",
        runs_db_path=db_path,
        **overrides,
    )
    return TestClient(create_app(settings))


def test_chat_persists_run_and_lists_it(tmp_path) -> None:
    client = _client_with_store(tmp_path)

    chat_response = client.post(
        "/v1/graph/chat",
        json={"messages": [{"role": "user", "content": "List high severity alerts"}]},
    )
    assert chat_response.status_code == 200
    payload = chat_response.json()
    assert payload["run_id"]

    list_response = client.get("/v1/runs")
    assert list_response.status_code == 200
    runs_payload = list_response.json()
    assert runs_payload["total"] == 1
    summary = runs_payload["runs"][0]
    assert summary["id"] == payload["run_id"]
    assert summary["status"] == "completed"
    assert summary["input_message"] == "List high severity alerts"
    assert summary["tool_call_count"] >= 1

    detail_response = client.get(f"/v1/runs/{payload['run_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["answer"] == payload["answer"]
    assert detail["tool_calls"]
    assert detail["trace_events"]


def test_chat_omits_run_id_when_store_disabled() -> None:
    settings = Settings(graph_backend="mock", llm_backend="fake", runs_enabled=False)
    client = TestClient(create_app(settings))

    response = client.post(
        "/v1/graph/chat",
        json={"messages": [{"role": "user", "content": "List users"}]},
    )

    assert response.status_code == 200
    assert response.json().get("run_id") is None


def test_runs_get_404_for_missing(tmp_path) -> None:
    client = _client_with_store(tmp_path)

    response = client.get("/v1/runs/does-not-exist")

    assert response.status_code == 404


def test_runs_endpoint_filters_by_tag(tmp_path) -> None:
    client = _client_with_store(tmp_path)

    client.post(
        "/v1/graph/chat",
        json={
            "messages": [{"role": "user", "content": "List users"}],
            "tags": {"eval_set": "mock", "scenario_id": "list_users"},
        },
    )
    client.post(
        "/v1/graph/chat",
        json={"messages": [{"role": "user", "content": "List users"}]},
    )

    tagged = client.get("/v1/runs", params={"tag_key": "eval_set", "tag_value": "mock"}).json()
    assert tagged["total"] == 1
    assert tagged["runs"][0]["tags"]["scenario_id"] == "list_users"


def test_run_store_env_var_parsing(monkeypatch, tmp_path) -> None:
    db_path = str(tmp_path / "runs.sqlite3")
    monkeypatch.setenv("RUNS_ENABLED", "true")
    monkeypatch.setenv("RUNS_DB_PATH", db_path)

    settings = Settings.from_env()

    assert settings.runs_enabled is True
    assert settings.runs_db_path == db_path

    # cleanup any cached DB on re-init
    if os.path.exists(db_path):
        os.remove(db_path)
