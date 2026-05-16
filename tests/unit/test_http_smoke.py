from fastapi.testclient import TestClient

from graph_harness.app.main import create_app
from graph_harness.core.config import Settings


def build_client(**settings_overrides) -> TestClient:
    settings = Settings(graph_backend="mock", llm_backend="fake", **settings_overrides)
    return TestClient(create_app(settings))


def test_health_endpoint() -> None:
    client = build_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_operations_endpoint_lists_mock_tools() -> None:
    client = build_client()

    response = client.get("/v1/graph/operations")

    assert response.status_code == 200
    payload = response.json()
    tool_names = {item["name"] for item in payload["operations"]}
    assert payload["operation_count"] >= 10
    assert {
        "list_users",
        "resolve_user",
        "list_security_alerts",
        "list_oauth_permission_grants",
        "delete_oauth_permission_grant",
    } <= tool_names


def test_chat_endpoint_uses_mock_agent_stack() -> None:
    client = build_client()

    response = client.post(
        "/v1/graph/chat",
        json={"messages": [{"role": "user", "content": "List high severity alerts"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["stop_reason"] == "final_answer"
    assert [record["name"] for record in payload["tool_calls"]] == ["list_security_alerts"]
    assert "alert-1" in payload["answer"]
    assert "trace_events" in payload
    assert "tool_calls_executed" in {event["event"] for event in payload["trace_events"]}


def test_chat_endpoint_returns_clarification_status() -> None:
    client = build_client()

    response = client.post(
        "/v1/graph/chat",
        json={"messages": [{"role": "user", "content": "Resolve Alex"}]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_clarification"
    assert payload["stop_reason"] == "clarification_ambiguous_identity"
    assert "multiple matching identities" in payload["answer"]
    assert "clarification_required" in {event["event"] for event in payload["trace_events"]}


def test_chat_stream_endpoint_returns_sse_events() -> None:
    client = build_client()

    response = client.post(
        "/v1/graph/chat/stream",
        json={"messages": [{"role": "user", "content": "Resolve Sarah"}]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert '"event":"result"' in response.text
    assert '"event":"done"' in response.text


def test_api_key_gate_rejects_missing_key() -> None:
    client = build_client(llm_api_key="secret")

    response = client.get("/v1/graph/operations")

    assert response.status_code == 401


def test_api_key_gate_accepts_configured_key() -> None:
    client = build_client(llm_api_key="secret")

    response = client.get("/v1/graph/operations", headers={"x-api-key": "secret"})

    assert response.status_code == 200
