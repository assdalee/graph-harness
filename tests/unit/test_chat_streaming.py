import json

from fastapi.testclient import TestClient

from graph_harness.app.main import create_app
from graph_harness.core.config import Settings


def _client() -> TestClient:
    return TestClient(create_app(Settings(graph_backend="mock", llm_backend="fake")))


def _parse_events(text: str) -> list[dict]:
    events = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


def test_stream_emits_trace_events_then_result_then_done() -> None:
    client = _client()
    response = client.post(
        "/v1/graph/chat/stream",
        json={"messages": [{"role": "user", "content": "List high severity alerts"}]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    events = _parse_events(response.text)
    kinds = [e["event"] for e in events]

    # At least one trace event arrives before the terminal result/done.
    assert "trace" in kinds
    assert kinds[-2:] == ["result", "done"]
    assert kinds.index("trace") < kinds.index("result")

    # Trace events carry the agent trace payload shape.
    first_trace = next(e for e in events if e["event"] == "trace")
    assert "event" in first_trace["data"]
    assert "turn" in first_trace["data"]

    # The result event carries the full ChatResponse.
    result = next(e for e in events if e["event"] == "result")
    assert result["data"]["status"] == "completed"
    assert [tc["name"] for tc in result["data"]["tool_calls"]] == ["list_security_alerts"]


def test_stream_includes_run_lifecycle_events() -> None:
    client = _client()
    response = client.post(
        "/v1/graph/chat/stream",
        json={"messages": [{"role": "user", "content": "List users"}]},
    )
    events = _parse_events(response.text)
    trace_names = {e["data"]["event"] for e in events if e["event"] == "trace"}
    assert "run_started" in trace_names
    assert "run_completed" in trace_names
