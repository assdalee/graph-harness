# GraphHarness

Production-oriented AI agent harness for Microsoft Graph, built with FastAPI and LiteLLM.

GraphHarness is not a flashy multi-agent demo. It is a small, explicit service for studying and
shipping reliable tool-using agents: typed tools, bounded loops, recovery policy, clarification
policy, mock evals, live Graph smoke checks, and traceable execution.

## Why This Exists

Many agent prototypes work once. GraphHarness focuses on what happens after the prototype:

- Can the agent call tools through typed contracts?
- Can it recover from transient or correctable failures?
- Can it stop and ask for clarification when continuing is unsafe?
- Can mutations require explicit confirmation?
- Can behavior be tested without real Microsoft Graph credentials?
- Can live credentials be checked without destructive actions?
- Can runs be inspected through trace events and structured responses?

The runtime is intentionally low-abstraction:

- no LangChain
- no LangGraph
- no global LLM objects initialized at import time
- no LLM calls inside tools
- no Graph auth inside the agent loop
- no FastAPI imports in business logic

## Architecture

```text
Client
  -> FastAPI routes
  -> ChatService
  -> GraphAgent
  -> LiteLLMClient or FakeLLMClient
  -> ToolExecutor
  -> GraphToolRegistry
  -> GraphClient or MockGraphClient
  -> Microsoft Graph API
```

Core layers:

- `app`: FastAPI app factory, routes, dependency wiring
- `services`: request-level orchestration
- `agent`: single-agent loop, policies, state, compaction, trace events
- `llm`: LiteLLM adapter, fake deterministic LLM, prompt text
- `tools`: typed tool contracts, executor, result/error envelopes
- `graph`: Microsoft Graph client, token provider, operation catalog, mock backend
- `evals`: deterministic mock scenarios
- `scripts`: quality gate, eval runner, live smoke checks

## Features

- Model-agnostic LLM access through LiteLLM
- FastAPI app factory with explicit dependency construction
- Typed Pydantic tool arguments
- Normalized `ToolResult` / `ToolError` envelopes
- Error taxonomy for validation, permission, rate limit, not found, ambiguity, and upstream errors
- Bounded agent loop with retry budgets and repeated-tool suppression
- Clarification policy for ambiguous identity and missing mutation confirmation
- Recovery policy for retryable tool failures
- Context compaction for long conversations
- Structured trace events returned in chat responses
- Optional structured trace logging
- Mock Microsoft Graph backend
- Fake deterministic LLM backend
- Mock eval scenarios
- Live read-only Microsoft Graph smoke test
- One-command quality gate

## Quickstart

```bash
cp .env.example .env
uv sync --extra dev
```

Run in local mock mode, without Microsoft Graph or real LLM credentials:

```bash
GRAPH_BACKEND=mock LLM_BACKEND=fake \
uv run uvicorn graph_harness.app.main:create_app --factory --host 0.0.0.0 --port 8091 --reload
```

Try a chat request:

```bash
curl -s http://localhost:8091/v1/graph/chat \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"List high severity alerts"}]}' | python3 -m json.tool
```

## API

- `GET /health`
- `GET /v1/graph/operations`
- `POST /v1/graph/chat`
- `POST /v1/graph/chat/stream`

## Frontend Console

GraphHarness includes a lightweight React console in `frontend/`.

Run the backend in one terminal:

```bash
GRAPH_BACKEND=mock LLM_BACKEND=fake \
uv run uvicorn graph_harness.app.main:create_app --factory --host 0.0.0.0 --port 8091 --reload
```

Run the frontend in another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to `http://localhost:8091`.

Build the frontend:

```bash
cd frontend
npm run build
```

## Docker

Run the full stack with Docker Compose:

```bash
GRAPH_BACKEND=mock LLM_BACKEND=fake docker compose up --build
```

Open `http://localhost:5173`. The frontend container serves the React build with Nginx and
proxies `/api` to the backend container.

Useful container endpoints:

```bash
curl -s http://localhost:8091/health
curl -s http://localhost:5173/healthz
```

To use live Microsoft Graph and a real LiteLLM provider, set the same environment variables
you use locally in `.env`, then run with the live override:

```bash
docker compose -f docker-compose.yml -f docker-compose.live.yml up --build
```

By default, Compose falls back to `GRAPH_BACKEND=mock` and `LLM_BACKEND=fake` when those
variables are not set, so the stack can run without Microsoft Graph or LLM credentials.

## Configuration

Important `.env` values:

```env
APP_NAME="GraphHarness"

LLM_BACKEND=fake
LLM_MODEL=openai/gpt-4o-mini
LITELLM_TEMPERATURE=0

GRAPH_BACKEND=mock
GRAPH_TENANT_ID=
GRAPH_CLIENT_ID=
GRAPH_CLIENT_SECRET=
GRAPH_SCOPES=https://graph.microsoft.com/.default

AGENT_MAX_TURNS=4
AGENT_MAX_TOOL_CALLS=8
AGENT_ENABLE_CLARIFICATION_POLICY=true
AGENT_ENABLE_CONTEXT_COMPACTION=true
AGENT_REQUIRE_MUTATION_CONFIRMATION=true
```

Set `LLM_MODEL` to any LiteLLM-supported model string, such as OpenAI, Azure OpenAI, Anthropic,
Gemini, Ollama, vLLM, or another OpenAI-compatible backend.

For deterministic no-LLM tests:

```env
LLM_BACKEND=fake
LLM_FAKE_SCENARIOS_PATH=evals/fake_llm_scenarios.json
```

## Testing

Run unit and API tests:

```bash
uv run pytest -q
```

Run deterministic mock evals:

```bash
uv run python scripts/run_mock_evals.py
```

Print full eval JSON:

```bash
uv run python scripts/run_mock_evals.py --json
```

Run the full local quality gate:

```bash
uv run python scripts/check.py
```

The quality gate runs compile checks, tests, frontend install/build, mock evals, app factory import,
and live smoke. The live smoke automatically skips when Graph credentials are absent.

## Live Microsoft Graph Smoke

For live read-only checks, create an Entra app registration with Microsoft Graph application
permissions such as:

```text
User.Read.All
Group.Read.All
GroupMember.Read.All
Application.Read.All
DelegatedPermissionGrant.Read.All
AuditLog.Read.All
Directory.Read.All
```

Then configure:

```env
GRAPH_BACKEND=live
GRAPH_TENANT_ID=<Directory tenant ID>
GRAPH_CLIENT_ID=<Application client ID>
GRAPH_CLIENT_SECRET=<Client secret Value>
GRAPH_SCOPES=https://graph.microsoft.com/.default
```

Run:

```bash
python3 scripts/live_smoke.py
```

The smoke test treats core directory checks as required and security-alert checks as optional, since
basic tenants are often not provisioned for Microsoft Defender/security data.

## Mutation Safety

Mutating tools are marked with `requires_confirmation`. When
`AGENT_REQUIRE_MUTATION_CONFIRMATION=true`, write operations must include:

```json
{
  "confirmed": true,
  "reason": "Why this mutation is being performed.",
  "target_display": "Human-readable target."
}
```

Without confirmation, the harness returns `status=needs_clarification` instead of executing the
mutation.

## Tool Result Contract

Tools return a normalized envelope:

```json
{
  "ok": true,
  "data": {},
  "summary": "Returned object with keys: id, displayName.",
  "identifiers": [{"id": "...", "displayName": "..."}],
  "error": null
}
```

Failures use structured error codes so the agent can decide whether to recover, clarify, or
finalize.

## Agent Reliability

The single-agent loop includes:

- max turn and max tool-call budgets
- LLM retry budget
- empty response recovery
- repeated identical tool-call suppression
- fallback answers from tool summaries
- recovery instructions for retryable errors
- terminal handling for unsafe or permission-blocked actions
- run metadata: `status`, `stop_reason`, `turns`, `warnings`, `trace_events`

## Project Status

GraphHarness is a portfolio and learning project for production-style AI agent engineering. It is
useful for studying reliable tool use, but it is not a finished enterprise security product. Use
mock mode for destructive scenarios and only run live mutations in disposable tenants with
purpose-built test objects.
