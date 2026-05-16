import json
import logging
from typing import Any

from graph_harness.agent.clarification import ClarificationPolicy
from graph_harness.agent.compaction import ContextCompactor
from graph_harness.agent.recovery import ErrorRecoveryPolicy
from graph_harness.agent.state import AgentRunState
from graph_harness.api_models.chat import AgentTraceEvent, ChatResponse
from graph_harness.core.config import Settings
from graph_harness.llm.client import LiteLLMClient
from graph_harness.llm.prompts import FINAL_RESPONSE_INSTRUCTION, GRAPH_AGENT_SYSTEM_PROMPT
from graph_harness.llm.types import LLMResponse, LLMToolCall
from graph_harness.tools.executor import ToolExecutor, extract_data
from graph_harness.tools.registry import ToolRegistry


logger = logging.getLogger(__name__)


class GraphAgent:
    """Thin custom agent loop.

    The loop is intentionally explicit: call model, execute tool calls, append results, repeat.
    """

    def __init__(
        self,
        *,
        llm_client: LiteLLMClient,
        registry: ToolRegistry,
        executor: ToolExecutor,
        settings: Settings,
    ) -> None:
        self._llm = llm_client
        self._registry = registry
        self._executor = executor
        self._settings = settings
        self._recovery_policy = ErrorRecoveryPolicy(settings)
        self._clarification_policy = ClarificationPolicy(settings)
        self._context_compactor = ContextCompactor(settings)

    async def run(self, *, messages: list[dict[str, Any]], thread_id: str | None = None) -> ChatResponse:
        state = AgentRunState(messages=self._initial_messages(messages))
        answer = ""
        tool_call_counts: dict[str, int] = {}
        self._trace(state, "run_started", "Agent run started.", thread_id=thread_id, message_count=len(messages))

        for turn in range(self._settings.agent_max_turns):
            state.turn = turn + 1
            self._trace(state, "turn_started", "Agent turn started.")
            response = await self._safe_complete(
                state,
                tools=self._registry.openai_tools(),
                tool_choice="auto",
            )
            if response is None:
                answer = self._fallback_answer(state)
                state.status = "failed"
                state.stop_reason = "llm_error"
                self._trace(state, "run_failed", "Stopping after LLM failure.", stop_reason=state.stop_reason)
                break

            if not response.tool_calls:
                content = response.content.strip()
                if content:
                    answer = content
                    state.messages.append({"role": "assistant", "content": answer})
                    state.status = "completed"
                    state.stop_reason = "final_answer"
                    self._trace(state, "final_answer", "Model returned final answer.")
                    break

                state.empty_response_count += 1
                state.warnings.append("Model returned an empty response with no tool calls.")
                self._trace(
                    state,
                    "empty_model_response",
                    "Model returned empty response with no tool calls.",
                    empty_response_count=state.empty_response_count,
                )
                if state.empty_response_count > self._settings.agent_empty_response_retries:
                    answer = self._fallback_answer(state)
                    state.status = "failed"
                    state.stop_reason = "empty_model_response"
                    self._trace(state, "run_failed", "Stopping after empty model responses.")
                    break
                state.messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was empty. Either call a relevant tool or "
                            "provide a final answer based on available tool results."
                        ),
                    }
                )
                continue

            calls = self._filter_tool_calls(response.tool_calls, tool_call_counts, state)
            if not calls:
                answer = await self._finalize_or_fallback(state, "repeated_tool_calls")
                break
            self._trace(
                state,
                "tool_calls_requested",
                "Model requested tool calls.",
                tools=[call.name for call in calls],
            )

            assistant_message = {
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {"name": call.name, "arguments": json.dumps(call.args)},
                    }
                    for call in calls
                ],
            }
            state.messages.append(assistant_message)

            records = await self._executor.execute_calls(calls)
            state.tool_calls.extend(records)
            state.data = extract_data(state.tool_calls)
            self._trace(
                state,
                "tool_calls_executed",
                "Tool calls executed.",
                tools=[record.name for record in records],
                error_codes=[record.error.code for record in records if record.error],
            )

            for record in records:
                tool_payload = record.result.model_dump(mode="json") if record.result else {}
                state.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": record.id,
                        "name": record.name,
                        "content": json.dumps(tool_payload, default=str),
                    }
                )

            clarification = self._clarification_policy.evaluate(records)
            if clarification is not None:
                state.warnings.append(clarification.warning)
                state.status = "needs_clarification"
                state.stop_reason = clarification.stop_reason
                answer = clarification.answer
                state.messages.append({"role": "assistant", "content": answer})
                self._trace(
                    state,
                    "clarification_required",
                    "Clarification policy stopped the run.",
                    stop_reason=state.stop_reason,
                )
                break

            directive = self._recovery_policy.evaluate(records, state)
            if directive is not None:
                state.warnings.append(directive.warning)
                state.messages.append({"role": "user", "content": directive.message})
                self._trace(
                    state,
                    "recovery_directive",
                    "Recovery policy produced a directive.",
                    action=directive.action,
                    stop_reason=directive.stop_reason,
                )
                if directive.action == "continue":
                    continue
                answer = await self._finalize_or_fallback(state, directive.stop_reason)
                break
        else:
            answer = await self._finalize_or_fallback(state, "max_turns")

        if not answer.strip() and state.tool_calls:
            answer = await self._finalize_or_fallback(state, "final_answer_empty")

        if not answer.strip():
            answer = self._fallback_answer(state)
            state.status = "failed"
            state.stop_reason = state.stop_reason or "no_answer"
            self._trace(state, "fallback_answer", "Generated fallback answer.", stop_reason=state.stop_reason)

        self._trace(
            state,
            "run_completed",
            "Agent run completed.",
            status=state.status,
            stop_reason=state.stop_reason,
            turns=state.turn,
            tool_call_count=len(state.tool_calls),
        )

        return ChatResponse(
            thread_id=thread_id,
            answer=answer,
            status=state.status,
            stop_reason=state.stop_reason,
            turns=state.turn,
            data=state.data,
            tool_calls=state.tool_calls,
            messages=state.messages,
            warnings=state.warnings,
            trace_events=state.trace_events,
        )

    def _initial_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        user_messages = [message for message in messages if message.get("role") != "system"]
        system_messages = [message for message in messages if message.get("role") == "system"]
        return [
            {"role": "system", "content": GRAPH_AGENT_SYSTEM_PROMPT},
            *system_messages,
            *user_messages,
        ]

    async def _finalize(self, state: AgentRunState) -> str:
        final_messages = [
            *state.messages,
            {"role": "user", "content": FINAL_RESPONSE_INSTRUCTION},
        ]
        response = await self._safe_complete(state, messages=final_messages, tools=None, tool_choice=None)
        if response is None:
            return ""
        content = response.content.strip()
        if content:
            state.messages.append({"role": "assistant", "content": content})
        return content

    async def _safe_complete(
        self,
        state: AgentRunState,
        *,
        tools: list[dict[str, Any]] | None,
        tool_choice: str | dict[str, Any] | None,
        messages: list[dict[str, Any]] | None = None,
    ) -> LLMResponse | None:
        attempts = self._settings.agent_llm_retries + 1
        source_messages = messages or state.messages
        llm_messages, compacted = self._context_compactor.compact(source_messages)
        if compacted:
            self._trace(
                state,
                "context_compacted",
                "Compacted context before LLM call.",
                original_message_count=len(source_messages),
                compacted_message_count=len(llm_messages),
            )
        for attempt in range(attempts):
            self._trace(
                state,
                "llm_call_started",
                "Calling LLM backend.",
                attempt=attempt + 1,
                tools_enabled=tools is not None,
            )
            try:
                response = await self._llm.complete(
                    messages=llm_messages,
                    tools=tools,
                    tool_choice=tool_choice,
                )
                self._trace(
                    state,
                    "llm_call_succeeded",
                    "LLM backend returned.",
                    attempt=attempt + 1,
                    tool_call_count=len(response.tool_calls),
                    has_content=bool(response.content.strip()),
                )
                return response
            except Exception as exc:
                logger.warning("LLM call failed on attempt %d/%d: %s", attempt + 1, attempts, exc)
                self._trace(
                    state,
                    "llm_call_failed",
                    "LLM backend call failed.",
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt == attempts - 1:
                    state.warnings.append(f"LLM call failed after {attempts} attempt(s): {exc}")
                    return None
        return None

    def _filter_tool_calls(
        self,
        calls: list[LLMToolCall],
        counts: dict[str, int],
        state: AgentRunState,
    ) -> list[LLMToolCall]:
        filtered: list[LLMToolCall] = []
        for call in calls[: self._settings.agent_max_tool_calls]:
            signature = json.dumps({"name": call.name, "args": call.args}, sort_keys=True, default=str)
            counts[signature] = counts.get(signature, 0) + 1
            if counts[signature] > self._settings.agent_repeated_tool_call_limit:
                state.warnings.append(f"Skipped repeated tool call: {call.name}.")
                self._trace(state, "tool_call_skipped", "Skipped repeated tool call.", tool=call.name)
                continue
            filtered.append(call)

        if len(calls) > self._settings.agent_max_tool_calls:
            state.warnings.append(
                f"Model requested {len(calls)} tool calls; limited to {self._settings.agent_max_tool_calls}."
            )
        return filtered

    async def _finalize_or_fallback(self, state: AgentRunState, stop_reason: str) -> str:
        state.stop_reason = stop_reason
        self._trace(state, "finalization_started", "Starting final response synthesis.", stop_reason=stop_reason)
        answer = await self._finalize(state)
        if answer.strip():
            state.status = "completed"
            self._trace(state, "finalization_succeeded", "Final response synthesis succeeded.")
            return answer
        state.status = "partial" if state.tool_calls else "failed"
        self._trace(state, "finalization_failed", "Final response synthesis failed; using fallback.")
        return self._fallback_answer(state)

    def _fallback_answer(self, state: AgentRunState) -> str:
        if state.tool_calls:
            summaries = [record.result.summary for record in state.tool_calls if record.result]
            errors = [
                f"{record.name}: {record.error.code} - {record.error.message}"
                for record in state.tool_calls
                if record.error
            ]
            lines = ["I could not get a final model-written answer, but tool execution produced results."]
            if summaries:
                lines.append("Tool summaries:")
                lines.extend(f"- {summary}" for summary in summaries[:8])
            if errors:
                lines.append("Tool errors:")
                lines.extend(f"- {error}" for error in errors[:5])
            return "\n".join(lines)
        return "I could not complete the request because the model did not return a usable response."

    def _trace(self, state: AgentRunState, event: str, message: str = "", **metadata: Any) -> None:
        trace_event = AgentTraceEvent(
            event=event,
            turn=state.turn,
            message=message,
            metadata=metadata,
        )
        state.trace_events.append(trace_event)
        if self._settings.agent_log_trace_events:
            logger.info(
                "agent_trace %s",
                trace_event.model_dump_json(),
                extra={"agent_event": event, "agent_turn": state.turn},
            )
