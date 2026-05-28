"""Abstract run store interface and persisted run record models for the runs subsystem."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

from graph_harness.api_models.chat import AgentTraceEvent, LLMCallRecord, ToolCallRecord


class RunSummary(BaseModel):
    """Lightweight run row for list views, carrying counts instead of full payloads."""

    model_config = ConfigDict(extra="ignore")

    id: str
    thread_id: str | None = None
    user_id: str | None = None
    created_at: datetime
    finished_at: datetime
    duration_ms: int
    input_message: str = ""
    llm_model: str | None = None
    llm_backend: str | None = None
    status: str
    stop_reason: str
    turns: int = 0
    tool_call_count: int = 0
    warning_count: int = 0
    tags: dict[str, Any] = Field(default_factory=dict)


class RunRecord(BaseModel):
    """Full persisted record of a single agent run, including messages, tool calls, and traces."""

    model_config = ConfigDict(extra="ignore")

    id: str
    thread_id: str | None = None
    user_id: str | None = None
    created_at: datetime
    finished_at: datetime
    duration_ms: int
    input_message: str = ""
    llm_model: str | None = None
    llm_backend: str | None = None
    status: str
    stop_reason: str
    turns: int = 0
    answer: str = ""
    warnings: list[str] = Field(default_factory=list)
    data: list[Any] = Field(default_factory=list)
    messages: list[dict[str, Any]] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)
    llm_calls: list[LLMCallRecord] = Field(default_factory=list)
    config_snapshot: dict[str, Any] = Field(default_factory=dict)
    tags: dict[str, Any] = Field(default_factory=dict)

    def to_summary(self) -> RunSummary:
        """Derive the lightweight summary view from this full record."""
        return RunSummary(
            id=self.id,
            thread_id=self.thread_id,
            user_id=self.user_id,
            created_at=self.created_at,
            finished_at=self.finished_at,
            duration_ms=self.duration_ms,
            input_message=self.input_message,
            llm_model=self.llm_model,
            llm_backend=self.llm_backend,
            status=self.status,
            stop_reason=self.stop_reason,
            turns=self.turns,
            tool_call_count=len(self.tool_calls),
            warning_count=len(self.warnings),
            tags=self.tags,
        )


class RunListFilters(BaseModel):
    """Query filters and pagination bounds for listing and counting stored runs."""

    status: str | None = None
    thread_id: str | None = None
    user_id: str | None = None
    tag_key: str | None = None
    tag_value: str | None = None
    since: datetime | None = None
    limit: int = 50
    offset: int = 0


class RunStore(Protocol):
    """Structural interface every run store backend must implement."""

    async def record(self, run: RunRecord) -> bool:
        """Persist a run (insert or upsert); return whether it was stored."""
        ...

    async def get(self, run_id: str) -> RunRecord | None:
        """Fetch a single run by id, or None if it does not exist."""
        ...

    async def list(self, filters: RunListFilters) -> list[RunSummary]:
        """Return run summaries matching the given filters."""
        ...

    async def count(self, filters: RunListFilters) -> int:
        """Return the number of runs matching the given filters."""
        ...


class NullRunStore:
    """No-op store used when persistence is disabled."""

    async def record(self, run: RunRecord) -> bool:
        """Discard the run and report that nothing was persisted."""
        return False

    async def get(self, run_id: str) -> RunRecord | None:
        """Return nothing since no runs are ever stored."""
        return None

    async def list(self, filters: RunListFilters) -> list[RunSummary]:
        """Return an empty list since no runs are ever stored."""
        return []

    async def count(self, filters: RunListFilters) -> int:
        """Return zero since no runs are ever stored."""
        return 0


def build_run_store(settings: Any) -> RunStore:
    """Construct the configured run store. Imported lazily to avoid circular deps."""
    if not getattr(settings, "runs_enabled", False):
        return NullRunStore()
    backend = (getattr(settings, "runs_backend", "sqlite") or "sqlite").lower()
    if backend == "sqlite":
        from graph_harness.runs.sqlite_store import SqliteRunStore

        return SqliteRunStore(settings.runs_db_path)
    if backend == "null":
        return NullRunStore()
    raise ValueError(f"Unknown runs_backend: {backend!r}")
