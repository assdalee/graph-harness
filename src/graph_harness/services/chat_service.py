"""Chat orchestration service wrapping the agent and optional run recording."""

import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from graph_harness.agent.agent import GraphAgent
from graph_harness.agent.policies import normalize_inbound_messages
from graph_harness.api_models.chat import AgentTraceEvent, ChatRequest, ChatResponse
from graph_harness.core.config import Settings
from graph_harness.runs.store import NullRunStore, RunRecord, RunStore


class ChatService:
    """Runs a chat request through the agent and persists the run when enabled."""

    def __init__(
        self,
        agent: GraphAgent,
        *,
        run_store: RunStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Wire the agent with an optional run store and settings snapshot."""
        self._agent = agent
        self._run_store = run_store or NullRunStore()
        self._settings = settings

    async def chat(
        self,
        request: ChatRequest,
        *,
        on_event: Callable[[AgentTraceEvent], None] | None = None,
    ) -> ChatResponse:
        """Run the request through the agent and record the run if a store is set."""
        normalized = request.normalized_input()
        messages = normalize_inbound_messages(normalized.messages)
        thread_id = normalized.thread_id or normalized.user_id

        started_at = datetime.now(timezone.utc)
        response = await self._agent.run(
            messages=messages, thread_id=thread_id, on_event=on_event
        )
        finished_at = datetime.now(timezone.utc)

        if isinstance(self._run_store, NullRunStore):
            return response

        run_id = str(uuid.uuid4())
        record = RunRecord(
            id=run_id,
            thread_id=response.thread_id,
            user_id=normalized.user_id,
            created_at=started_at,
            finished_at=finished_at,
            duration_ms=int((finished_at - started_at).total_seconds() * 1000),
            input_message=_first_user_message(messages),
            llm_model=getattr(self._settings, "llm_model", None) if self._settings else None,
            llm_backend=getattr(self._settings, "llm_backend", None) if self._settings else None,
            status=response.status,
            stop_reason=response.stop_reason,
            turns=response.turns,
            answer=response.answer,
            warnings=list(response.warnings),
            data=list(response.data),
            messages=list(response.messages),
            tool_calls=list(response.tool_calls),
            trace_events=list(response.trace_events),
            llm_calls=list(response.llm_calls),
            config_snapshot=_config_snapshot(self._settings),
            tags=dict(request.tags or {}),
        )
        if await self._run_store.record(record):
            response.run_id = run_id
        return response


def _first_user_message(messages: list[dict]) -> str:
    """Return the first user message text for run-record indexing."""
    for message in messages:
        if message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, str):
                return content
    return ""


def _config_snapshot(settings: Settings | None) -> dict:
    """Capture the config fields worth recording alongside a run."""
    if settings is None:
        return {}
    return {
        "llm_model": settings.llm_model,
        "llm_backend": settings.llm_backend,
        "graph_backend": settings.graph_backend,
        "agent_max_turns": settings.agent_max_turns,
        "agent_max_tool_calls": settings.agent_max_tool_calls,
    }
