import logging

from fastapi.testclient import TestClient

from graph_harness.agent.compaction import ContextCompactor
from graph_harness.app.main import create_app
from graph_harness.core.config import Settings
from graph_harness.core.logging import RequestIdFilter, set_request_id


def _client(**overrides) -> TestClient:
    return TestClient(create_app(Settings(graph_backend="mock", llm_backend="fake", **overrides)))


# --- request size limit -------------------------------------------------


def test_oversized_request_rejected_with_413() -> None:
    client = _client(max_request_bytes=2048)
    big = "x" * 5000
    response = client.post(
        "/v1/graph/chat",
        json={"messages": [{"role": "user", "content": big}]},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "request_too_large"


def test_normal_request_passes_size_check() -> None:
    client = _client(max_request_bytes=1_000_000)
    response = client.post(
        "/v1/graph/chat",
        json={"messages": [{"role": "user", "content": "List users"}]},
    )
    assert response.status_code == 200


# --- request id correlation --------------------------------------------


def test_response_carries_request_id_header() -> None:
    client = _client()
    response = client.get("/health")
    assert response.headers.get("x-request-id")


def test_incoming_request_id_is_echoed() -> None:
    client = _client()
    response = client.get("/health", headers={"x-request-id": "trace-123"})
    assert response.headers["x-request-id"] == "trace-123"


def test_request_id_filter_injects_attribute() -> None:
    set_request_id("abc")
    record = logging.LogRecord("n", logging.INFO, "f", 1, "msg", None, None)
    assert RequestIdFilter().filter(record) is True
    assert record.request_id == "abc"


# --- compaction robustness ---------------------------------------------


def test_compaction_splits_by_index_with_duplicate_messages() -> None:
    settings = Settings(agent_context_recent_messages=4)
    compactor = ContextCompactor(settings)
    # Identical dict values would collapse under an id()/equality-based split;
    # an index-based split keeps the correct recent window.
    messages = [{"role": "system", "content": "sys"}]
    messages += [{"role": "user", "content": "dup"} for _ in range(10)]

    compacted, did_compact = compactor.compact(messages)

    assert did_compact is True
    # The last 4 messages must be preserved verbatim as the recent window.
    assert compacted[-4:] == messages[-4:]
    assert len(compacted) < len(messages)
