# GraphHarness Architecture

GraphHarness is a low-abstraction AI agent harness for Microsoft Graph. The runtime is organized
around explicit interfaces rather than an agent framework.

## Request Flow

```text
FastAPI route
  -> ChatService
  -> GraphAgent
  -> LiteLLMClient
  -> ToolExecutor
  -> ToolDefinition handler
  -> GraphClient
  -> Microsoft Graph API
```

## Layers

- `app`: FastAPI app construction, routes, dependency accessors.
- `api_models`: Pydantic request/response contracts.
- `services`: Application use cases. Routes delegate here.
- `agent`: The custom agent loop and message normalization policies.
- `llm`: LiteLLM adapter and prompt text.
- `tools`: Tool definitions, registry, validation, and execution policy.
- `graph`: Microsoft Graph auth, HTTP client, and operation catalog.
- `core`: Configuration, error, logging, and API-key helpers.

## Agent Loop

The agent loop does only four things:

1. Send normalized messages and tool schemas to LiteLLM.
2. Execute returned tool calls after validation and policy checks.
3. Append tool results back into the conversation.
4. Stop on a final answer or synthesize one after the max-turn guard.

Read-only tool batches can run concurrently. Mutations always go through confirmation policy and run
through normal validated tool execution.

Robustness controls live in the harness instead of the prompt:

- `AGENT_MAX_TURNS`: hard cap on tool/finalization rounds.
- `AGENT_MAX_TOOL_CALLS`: per-turn cap on model-requested tools.
- `AGENT_LLM_RETRIES`: retry budget around LiteLLM calls.
- `AGENT_EMPTY_RESPONSE_RETRIES`: lets the loop recover from empty model responses.
- `AGENT_REPEATED_TOOL_CALL_LIMIT`: suppresses repeated identical tool calls.
- `AGENT_ENABLE_CONTEXT_COMPACTION`: sends compact history to the LLM while retaining raw messages.
- `AGENT_CONTEXT_RECENT_MESSAGES`: number of recent messages preserved verbatim.
- `AGENT_CONTEXT_MAX_TOOL_CHARS`: max characters for compacted prior tool summary.

Responses include `status`, `stop_reason`, `turns`, and `warnings` so clients can distinguish a
clean final answer from partial/fallback execution. If final synthesis fails after tools ran, the
harness returns a deterministic fallback answer built from tool summaries and errors.

Every response also includes `trace_events`, a structured run log with event names, turn numbers,
messages, and metadata. Current events include LLM calls, tool requests, tool execution, recovery
directives, clarification stops, finalization, and run completion.
When `AGENT_LOG_TRACE_EVENTS=true`, the same trace events are emitted as structured JSON log lines.

## Clarification Policy

The `ClarificationPolicy` stops the loop when asking the user is safer than retrying:

- `confirmation_required`: returns `status=needs_clarification` and asks for the exact action,
  target, and reason before a mutation is attempted.
- `ambiguous_identity`: returns `status=needs_clarification` and lists the matching users/groups so
  the user can choose a stable identifier.

Clarification happens before recovery/finalization, so the model does not get a chance to improvise
around safety-sensitive ambiguity.

## Context Compaction

The `ContextCompactor` builds a reduced LLM input once conversations grow past the configured recent
message window. The raw `state.messages` are still retained and returned in API responses, but model
calls receive a compact view containing:

- the system prompt
- original user intent
- compacted prior assistant notes
- compacted tool summaries
- preserved identifiers from tool results
- recovery/clarification directives
- the most recent messages verbatim

When compaction happens, the run emits a `context_compacted` trace event with original and compacted
message counts.

## Error Recovery

Typed tool errors are handled by a harness-level `ErrorRecoveryPolicy` before the next model turn.
The policy keeps a small recovery attempt counter and converts error codes into explicit next steps:

- `invalid_filter`: retry once with safer structured filters or a broader fetch.
- `validation_error`: repair schema-invalid arguments once.
- `not_found`: try resolver tools when identity lookup may be the issue.
- `rate_limited`, `transient_graph_error`, `upstream_error`: retry only when the request can be made safer.
- `permission_denied`: finalize with required permission/admin-consent guidance.
- `confirmation_required`: ask for explicit mutation confirmation.
- `ambiguous_identity`: ask the user to choose the exact identity.
- `unknown_tool`: explain unavailable operation coverage.

`AGENT_RECOVERY_MAX_ATTEMPTS` controls retry budget per tool/error pair. Once exhausted, the loop
finalizes instead of spinning.

## Model Agnosticism

The rest of the app depends only on `LiteLLMClient`, not on any vendor SDK. `LLM_MODEL` can point to
OpenAI, Azure OpenAI, Anthropic, Gemini, Ollama, vLLM, or any LiteLLM-supported provider.

For local no-credential testing, `LLM_BACKEND=fake` swaps in a deterministic `FakeLLMClient`.
`GRAPH_BACKEND=mock` swaps in an in-memory `MockGraphClient`. This lets evals exercise the real
FastAPI/service/agent/tool stack without Microsoft Graph credentials.
`LLM_FAKE_SCENARIOS_PATH` can point to declarative fake-LLM scenarios with `{match, tool, args}`
entries.

## Evals

`scripts/run_mock_evals.py` loads `evals/mock_scenarios.json`, builds the app with
`GRAPH_BACKEND=mock` and `LLM_BACKEND=fake`, then checks:

- status and stop reason
- expected tool sequence
- expected warning text
- expected trace events
- expected answer fragments

These evals are not a replacement for live Microsoft Graph smoke tests, but they validate the agent
harness without credentials.

`scripts/check.py` is the local quality gate. It runs compile checks, unit tests, mock evals, app
factory import, and `scripts/live_smoke.py`, which auto-skips when Graph credentials are absent.

## Tool Contract

Each tool has:

- name
- description
- Pydantic args model
- read-only classification
- confirmation requirement
- handler callable

This makes tool schemas, runtime validation, and execution policy testable without an LLM.

Every executed tool is normalized into a `ToolResult` envelope:

```json
{
  "ok": true,
  "data": {},
  "summary": "Returned 1 record(s).",
  "identifiers": [{"id": "...", "displayName": "..."}],
  "error": null
}
```

Errors use a stable taxonomy instead of plain strings:

- `validation_error`
- `confirmation_required`
- `permission_denied`
- `not_found`
- `invalid_filter`
- `rate_limited`
- `transient_graph_error`
- `upstream_error`
- `unknown_tool`
- `ambiguous_identity`

Mutating tools inherit `ConfirmableArgs`, which includes `confirmed`, `reason`, and
`target_display`. When `confirmed=true`, `reason` is required so mutation attempts have a useful
audit trail.

Identity-sensitive workflows should use `resolve_user` and `resolve_group` before mutations. List
tools include pagination controls: `top`, `all_pages`, and `max_pages`. Security and log tools expose
structured filters such as `severity`, `status`, `created_after`, `assigned_to`, and
`user_principal_name` so the agent does not have to freestyle OData for common cases.
