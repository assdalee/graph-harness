from graph_harness.agent.recovery import ErrorRecoveryPolicy
from graph_harness.agent.state import AgentRunState
from graph_harness.api_models.chat import ToolCallRecord
from graph_harness.core.config import Settings
from graph_harness.tools.results import ToolError, ToolResult


def _record(code: str, name: str = "list_users") -> ToolCallRecord:
    error = ToolError(code=code, message=f"{code} happened")
    return ToolCallRecord(
        id="c1",
        name=name,
        args={},
        result=ToolResult(ok=False, error=error),
        error=error,
        read_only=True,
    )


def _state() -> AgentRunState:
    return AgentRunState(messages=[])


def test_no_errors_returns_none() -> None:
    policy = ErrorRecoveryPolicy(Settings())
    ok_record = ToolCallRecord(id="c", name="list_users", args={}, read_only=True)
    assert policy.evaluate([ok_record], _state()) is None


def test_terminal_code_finalizes() -> None:
    policy = ErrorRecoveryPolicy(Settings())
    directive = policy.evaluate([_record("permission_denied")], _state())
    assert directive is not None
    assert directive.action == "finalize"
    assert directive.stop_reason == "tool_error_permission_denied"


def test_retryable_code_continues_within_budget() -> None:
    policy = ErrorRecoveryPolicy(Settings(agent_recovery_max_attempts=1))
    state = _state()
    directive = policy.evaluate([_record("transient_graph_error")], state)
    assert directive is not None
    assert directive.action == "continue"
    assert directive.stop_reason == "recovering_tool_error"


def test_retryable_code_finalizes_when_exhausted() -> None:
    policy = ErrorRecoveryPolicy(Settings(agent_recovery_max_attempts=1))
    state = _state()
    records = [_record("transient_graph_error")]
    first = policy.evaluate(records, state)
    second = policy.evaluate(records, state)
    assert first.action == "continue"
    assert second.action == "finalize"
    assert second.stop_reason == "recovery_exhausted"


def test_terminal_wins_over_retryable() -> None:
    policy = ErrorRecoveryPolicy(Settings())
    directive = policy.evaluate(
        [_record("transient_graph_error"), _record("ambiguous_identity")], _state()
    )
    assert directive.action == "finalize"
    assert directive.stop_reason == "tool_error_ambiguous_identity"
