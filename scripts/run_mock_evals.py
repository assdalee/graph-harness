from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from graph_harness.api_models.chat import ChatMessageIn, ChatRequest
from graph_harness.app.main import create_app
from graph_harness.core.config import Settings


DEFAULT_SCENARIOS = ROOT / "evals" / "mock_scenarios.json"


async def run_scenario(service: Any, scenario: dict[str, Any]) -> dict[str, Any]:
    request = ChatRequest(
        messages=[ChatMessageIn(role="user", content=scenario["message"])],
        thread_id=f"eval-{scenario['id']}",
    )
    response = await service.chat(request)
    failures = assert_response(scenario, response)
    return {
        "id": scenario["id"],
        "passed": not failures,
        "failures": failures,
        "status": response.status,
        "stop_reason": response.stop_reason,
        "tools": [record.name for record in response.tool_calls],
        "warnings": response.warnings,
        "trace_events": [event.event for event in response.trace_events],
        "answer": response.answer,
    }


def assert_response(scenario: dict[str, Any], response: Any) -> list[str]:
    failures: list[str] = []
    if expected := scenario.get("expect_status"):
        if response.status != expected:
            failures.append(f"status expected {expected!r}, got {response.status!r}")
    if expected := scenario.get("expect_stop_reason"):
        if response.stop_reason != expected:
            failures.append(f"stop_reason expected {expected!r}, got {response.stop_reason!r}")
    if expected := scenario.get("expect_tool_names"):
        actual = [record.name for record in response.tool_calls]
        if actual != expected:
            failures.append(f"tools expected {expected!r}, got {actual!r}")
    if expected := scenario.get("expect_error_codes"):
        actual = [record.error.code for record in response.tool_calls if record.error]
        if actual != expected:
            failures.append(f"error codes expected {expected!r}, got {actual!r}")
    if expected := scenario.get("expect_tool_ok"):
        actual = [bool(record.result and record.result.ok) for record in response.tool_calls]
        if actual != expected:
            failures.append(f"tool ok flags expected {expected!r}, got {actual!r}")
    for text in scenario.get("expect_answer_contains", []):
        if text not in response.answer:
            failures.append(f"answer did not contain {text!r}")
    warnings = "\n".join(response.warnings)
    for text in scenario.get("expect_warning_contains", []):
        if text not in warnings:
            failures.append(f"warnings did not contain {text!r}")
    trace_events = [event.event for event in response.trace_events]
    for event in scenario.get("expect_trace_events", []):
        if event not in trace_events:
            failures.append(f"trace events did not contain {event!r}")
    return failures


async def main() -> int:
    parser = argparse.ArgumentParser(description="Run mock agent eval scenarios.")
    parser.add_argument("--scenarios", type=Path, default=DEFAULT_SCENARIOS)
    parser.add_argument("--json", action="store_true", help="Print full JSON results.")
    args = parser.parse_args()

    scenarios = json.loads(args.scenarios.read_text())
    app = create_app(
        Settings(
            graph_backend="mock",
            llm_backend="fake",
            llm_fake_scenarios_path=str(Path(__file__).resolve().parents[1] / "evals" / "fake_llm_scenarios.json"),
            agent_max_turns=5,
            agent_recovery_max_attempts=1,
        )
    )
    service = app.state.chat_service
    results = [await run_scenario(service, scenario) for scenario in scenarios]

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for result in results:
            marker = "PASS" if result["passed"] else "FAIL"
            print(f"{marker} {result['id']} status={result['status']} stop={result['stop_reason']}")
            for failure in result["failures"]:
                print(f"  - {failure}")

    failed = sum(1 for result in results if not result["passed"])
    print(f"\n{len(results) - failed}/{len(results)} scenarios passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
