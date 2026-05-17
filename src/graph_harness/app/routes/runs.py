from collections.abc import Callable
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from graph_harness.app.dependencies import get_run_store
from graph_harness.runs.store import NullRunStore, RunListFilters, RunRecord, RunStore, RunSummary


class RunListResponse(BaseModel):
    runs: list[RunSummary] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0


def create_runs_router(auth_dependency: Callable) -> APIRouter:
    router = APIRouter(prefix="/v1/runs", tags=["runs"], dependencies=[Depends(auth_dependency)])

    @router.get("", response_model=RunListResponse)
    async def list_runs(
        store: RunStore = Depends(get_run_store),
        status: str | None = Query(default=None),
        thread_id: str | None = Query(default=None),
        user_id: str | None = Query(default=None),
        tag_key: str | None = Query(default=None),
        tag_value: str | None = Query(default=None),
        since: datetime | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=500),
        offset: int = Query(default=0, ge=0),
    ) -> RunListResponse:
        _ensure_store_enabled(store)
        filters = RunListFilters(
            status=status,
            thread_id=thread_id,
            user_id=user_id,
            tag_key=tag_key,
            tag_value=tag_value,
            since=since,
            limit=limit,
            offset=offset,
        )
        runs = await store.list(filters)
        total = await store.count(filters)
        return RunListResponse(runs=runs, total=total, limit=limit, offset=offset)

    @router.get("/{run_id}", response_model=RunRecord)
    async def get_run(
        run_id: str,
        store: RunStore = Depends(get_run_store),
    ) -> RunRecord:
        _ensure_store_enabled(store)
        record = await store.get(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="run not found")
        return record

    return router


def _ensure_store_enabled(store: RunStore) -> None:
    if isinstance(store, NullRunStore):
        raise HTTPException(status_code=404, detail="run store disabled")
