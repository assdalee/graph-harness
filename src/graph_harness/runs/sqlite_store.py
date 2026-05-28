"""SQLite-backed run store implementation built on the stdlib sqlite3 module."""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from graph_harness.runs.store import RunListFilters, RunRecord, RunSummary


logger = logging.getLogger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  thread_id TEXT,
  user_id TEXT,
  created_at TEXT NOT NULL,
  finished_at TEXT NOT NULL,
  duration_ms INTEGER NOT NULL,
  input_message TEXT NOT NULL DEFAULT '',
  llm_model TEXT,
  llm_backend TEXT,
  status TEXT NOT NULL,
  stop_reason TEXT NOT NULL,
  turns INTEGER NOT NULL DEFAULT 0,
  tool_call_count INTEGER NOT NULL DEFAULT 0,
  warning_count INTEGER NOT NULL DEFAULT 0,
  answer TEXT NOT NULL DEFAULT '',
  warnings TEXT NOT NULL DEFAULT '[]',
  data TEXT NOT NULL DEFAULT '[]',
  messages TEXT NOT NULL DEFAULT '[]',
  config_snapshot TEXT NOT NULL DEFAULT '{}',
  tags TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_thread_id ON runs(thread_id);
CREATE INDEX IF NOT EXISTS idx_runs_user_id ON runs(user_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);

CREATE TABLE IF NOT EXISTS tool_calls (
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL,
  call_id TEXT NOT NULL,
  name TEXT NOT NULL,
  args TEXT NOT NULL DEFAULT '{}',
  result TEXT,
  error TEXT,
  read_only INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY (run_id, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_tool_calls_name ON tool_calls(name);

CREATE TABLE IF NOT EXISTS trace_events (
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL,
  turn INTEGER NOT NULL DEFAULT 0,
  event TEXT NOT NULL,
  message TEXT NOT NULL DEFAULT '',
  metadata TEXT NOT NULL DEFAULT '{}',
  PRIMARY KEY (run_id, ordinal)
);

CREATE INDEX IF NOT EXISTS idx_trace_events_event ON trace_events(event);

CREATE TABLE IF NOT EXISTS llm_calls (
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL,
  turn INTEGER NOT NULL DEFAULT 0,
  phase TEXT NOT NULL DEFAULT 'turn',
  compacted INTEGER NOT NULL DEFAULT 0,
  tool_count INTEGER NOT NULL DEFAULT 0,
  messages TEXT NOT NULL DEFAULT '[]',
  PRIMARY KEY (run_id, ordinal)
);
"""


class SqliteRunStore:
    """SQLite-backed RunStore. Blocking calls are wrapped in `asyncio.to_thread`."""

    def __init__(self, db_path: str) -> None:
        """Store the database path and defer schema creation until first use."""
        self._db_path = db_path
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Create the schema once, guarding concurrent first-use with a lock."""
        if self._initialized:
            return
        async with self._lock:
            if self._initialized:
                return
            await asyncio.to_thread(self._init_schema)
            self._initialized = True

    def _init_schema(self) -> None:
        """Ensure the parent directory exists and apply the table/index schema."""
        directory = Path(self._db_path).expanduser().resolve().parent
        directory.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Open a tuned connection with WAL, row access, and foreign keys enabled."""
        conn = sqlite3.connect(
            self._db_path,
            isolation_level=None,
            timeout=30.0,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA synchronous = NORMAL")
        return conn

    async def record(self, run: RunRecord) -> bool:
        """Persist a run off-thread, swallowing failures so observability never breaks a request."""
        try:
            await self._ensure_initialized()
            await asyncio.to_thread(self._record_sync, run)
            return True
        except Exception as exc:
            logger.warning("Failed to persist run %s: %s", run.id, exc)
            return False

    def _record_sync(self, run: RunRecord) -> None:
        """Upsert the run and rewrite its child rows in a single transaction."""
        with self._connect() as conn:
            conn.execute("BEGIN")
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (
                  id, thread_id, user_id, created_at, finished_at, duration_ms,
                  input_message, llm_model, llm_backend, status, stop_reason, turns,
                  tool_call_count, warning_count, answer, warnings, data, messages,
                  config_snapshot, tags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.id,
                    run.thread_id,
                    run.user_id,
                    _iso(run.created_at),
                    _iso(run.finished_at),
                    run.duration_ms,
                    run.input_message,
                    run.llm_model,
                    run.llm_backend,
                    run.status,
                    run.stop_reason,
                    run.turns,
                    len(run.tool_calls),
                    len(run.warnings),
                    run.answer,
                    json.dumps(run.warnings, default=str),
                    json.dumps(run.data, default=str),
                    json.dumps(run.messages, default=str),
                    json.dumps(run.config_snapshot, default=str),
                    json.dumps(run.tags, default=str),
                ),
            )
            conn.execute("DELETE FROM tool_calls WHERE run_id = ?", (run.id,))
            conn.execute("DELETE FROM trace_events WHERE run_id = ?", (run.id,))
            conn.execute("DELETE FROM llm_calls WHERE run_id = ?", (run.id,))
            conn.executemany(
                """
                INSERT INTO tool_calls (
                  run_id, ordinal, call_id, name, args, result, error, read_only
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run.id,
                        ordinal,
                        record.id,
                        record.name,
                        json.dumps(record.args, default=str),
                        json.dumps(record.result.model_dump(mode="json"), default=str)
                        if record.result is not None
                        else None,
                        json.dumps(record.error.model_dump(mode="json"), default=str)
                        if record.error is not None
                        else None,
                        1 if record.read_only else 0,
                    )
                    for ordinal, record in enumerate(run.tool_calls)
                ],
            )
            conn.executemany(
                """
                INSERT INTO trace_events (
                  run_id, ordinal, turn, event, message, metadata
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run.id,
                        ordinal,
                        event.turn,
                        event.event,
                        event.message,
                        json.dumps(event.metadata, default=str),
                    )
                    for ordinal, event in enumerate(run.trace_events)
                ],
            )
            conn.executemany(
                """
                INSERT INTO llm_calls (
                  run_id, ordinal, turn, phase, compacted, tool_count, messages
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        run.id,
                        ordinal,
                        call.turn,
                        call.phase,
                        1 if call.compacted else 0,
                        call.tool_count,
                        json.dumps(call.messages, default=str),
                    )
                    for ordinal, call in enumerate(run.llm_calls)
                ],
            )
            conn.execute("COMMIT")

    async def get(self, run_id: str) -> RunRecord | None:
        """Fetch a full run record by id off-thread."""
        await self._ensure_initialized()
        return await asyncio.to_thread(self._get_sync, run_id)

    def _get_sync(self, run_id: str) -> RunRecord | None:
        """Read the run and its child rows, reassembling them into a RunRecord."""
        with self._connect() as conn:
            run_row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
            if run_row is None:
                return None
            tool_rows = conn.execute(
                "SELECT * FROM tool_calls WHERE run_id = ? ORDER BY ordinal",
                (run_id,),
            ).fetchall()
            trace_rows = conn.execute(
                "SELECT * FROM trace_events WHERE run_id = ? ORDER BY ordinal",
                (run_id,),
            ).fetchall()
            llm_rows = conn.execute(
                "SELECT * FROM llm_calls WHERE run_id = ? ORDER BY ordinal",
                (run_id,),
            ).fetchall()
        return _record_from_rows(run_row, tool_rows, trace_rows, llm_rows)

    async def list(self, filters: RunListFilters) -> list[RunSummary]:
        """Return matching run summaries, newest first, off-thread."""
        await self._ensure_initialized()
        return await asyncio.to_thread(self._list_sync, filters)

    def _list_sync(self, filters: RunListFilters) -> list[RunSummary]:
        """Query summaries with the filters applied, clamping limit and offset to safe bounds."""
        sql, params = _build_where(filters)
        limit = max(1, min(filters.limit, 500))
        offset = max(0, filters.offset)
        query = f"SELECT * FROM runs {sql} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params = (*params, limit, offset)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_summary_from_row(row) for row in rows]

    async def count(self, filters: RunListFilters) -> int:
        """Return the total number of runs matching the filters off-thread."""
        await self._ensure_initialized()
        return await asyncio.to_thread(self._count_sync, filters)

    def _count_sync(self, filters: RunListFilters) -> int:
        """Count runs matching the filters, ignoring limit and offset."""
        sql, params = _build_where(filters)
        query = f"SELECT COUNT(*) AS n FROM runs {sql}"
        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
        return int(row["n"]) if row else 0


def _build_where(filters: RunListFilters) -> tuple[str, tuple[Any, ...]]:
    """Build a parameterized WHERE clause and its bind values from the filters."""
    clauses: list[str] = []
    params: list[Any] = []
    if filters.status:
        clauses.append("status = ?")
        params.append(filters.status)
    if filters.thread_id:
        clauses.append("thread_id = ?")
        params.append(filters.thread_id)
    if filters.user_id:
        clauses.append("user_id = ?")
        params.append(filters.user_id)
    if filters.since:
        clauses.append("created_at >= ?")
        params.append(_iso(filters.since))
    if filters.tag_key:
        tag_path = _json_path(filters.tag_key)
        if filters.tag_value is None:
            clauses.append("json_type(tags, ?) IS NOT NULL")
            params.append(tag_path)
        else:
            clauses.append("json_extract(tags, ?) = ?")
            params.append(tag_path)
            params.append(filters.tag_value)
    if not clauses:
        return "", ()
    return "WHERE " + " AND ".join(clauses), tuple(params)


def _summary_from_row(row: sqlite3.Row) -> RunSummary:
    """Map a runs table row to a RunSummary."""
    return RunSummary(
        id=row["id"],
        thread_id=row["thread_id"],
        user_id=row["user_id"],
        created_at=_parse_iso(row["created_at"]),
        finished_at=_parse_iso(row["finished_at"]),
        duration_ms=row["duration_ms"],
        input_message=row["input_message"] or "",
        llm_model=row["llm_model"],
        llm_backend=row["llm_backend"],
        status=row["status"],
        stop_reason=row["stop_reason"],
        turns=row["turns"],
        tool_call_count=row["tool_call_count"],
        warning_count=row["warning_count"],
        tags=_loads(row["tags"], {}),
    )


def _record_from_rows(
    run_row: sqlite3.Row,
    tool_rows: list[sqlite3.Row],
    trace_rows: list[sqlite3.Row],
    llm_rows: list[sqlite3.Row] | None = None,
) -> RunRecord:
    """Reassemble a full RunRecord from its run row and ordered child rows."""
    return RunRecord(
        id=run_row["id"],
        thread_id=run_row["thread_id"],
        user_id=run_row["user_id"],
        created_at=_parse_iso(run_row["created_at"]),
        finished_at=_parse_iso(run_row["finished_at"]),
        duration_ms=run_row["duration_ms"],
        input_message=run_row["input_message"] or "",
        llm_model=run_row["llm_model"],
        llm_backend=run_row["llm_backend"],
        status=run_row["status"],
        stop_reason=run_row["stop_reason"],
        turns=run_row["turns"],
        answer=run_row["answer"] or "",
        warnings=_loads(run_row["warnings"], []),
        data=_loads(run_row["data"], []),
        messages=_loads(run_row["messages"], []),
        tool_calls=[
            {
                "id": row["call_id"],
                "name": row["name"],
                "args": _loads(row["args"], {}),
                "result": _loads(row["result"], None) if row["result"] else None,
                "error": _loads(row["error"], None) if row["error"] else None,
                "read_only": bool(row["read_only"]),
            }
            for row in tool_rows
        ],
        trace_events=[
            {
                "event": row["event"],
                "turn": row["turn"],
                "message": row["message"] or "",
                "metadata": _loads(row["metadata"], {}),
            }
            for row in trace_rows
        ],
        llm_calls=[
            {
                "turn": row["turn"],
                "phase": row["phase"],
                "compacted": bool(row["compacted"]),
                "tool_count": row["tool_count"],
                "messages": _loads(row["messages"], []),
            }
            for row in (llm_rows or [])
        ],
        config_snapshot=_loads(run_row["config_snapshot"], {}),
        tags=_loads(run_row["tags"], {}),
    )


def _iso(value: datetime) -> str:
    """Serialize a datetime to a UTC ISO string, treating naive values as UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _parse_iso(value: str) -> datetime:
    """Parse a stored ISO timestamp string back into a datetime."""
    return datetime.fromisoformat(value)


def _json_path(key: str) -> str:
    """Build a JSON path expression for a tag key, quoting it to allow arbitrary characters."""
    return "$." + json.dumps(key)


def _loads(value: str | None, default: Any) -> Any:
    """Decode a JSON column value, falling back to a default on null or malformed data."""
    if value is None:
        return default
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return default
