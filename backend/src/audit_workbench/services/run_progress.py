from __future__ import annotations

import time
from typing import Any

from audit_workbench.db.models import Run
from audit_workbench.services.run_progress_plan import (
    StepStatus,
    _queue_wait_detail,
    _step,
    build_run_progress_plan,
)
from audit_workbench.settings import get_settings

_last_progress_commit: dict[str, float] = {}
_MAX_PROGRESS_CACHE = 512

__all__ = [
    "StepStatus",
    "_last_progress_commit",
    "_step",
    "build_run_progress_plan",
    "clear_progress_commit_cache",
    "fail_run_progress",
    "init_queued_progress",
    "mark_step_done",
    "progress_snapshot",
    "set_run_progress",
]


def clear_progress_commit_cache(run_id: str | None = None) -> None:
    if run_id:
        _last_progress_commit.pop(run_id, None)
    else:
        _last_progress_commit.clear()


def _touch_progress_cache(run_id: str, now: float) -> None:
    if run_id in _last_progress_commit:
        _last_progress_commit.pop(run_id)
    _last_progress_commit[run_id] = now
    while len(_last_progress_commit) > _MAX_PROGRESS_CACHE:
        _last_progress_commit.pop(next(iter(_last_progress_commit)))


def progress_snapshot(
    steps: list[dict[str, Any]],
    current_index: int,
    label: str,
) -> dict[str, Any]:
    out_steps: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        if index < current_index:
            status: StepStatus = "done"
        elif index == current_index:
            status = "active"
        else:
            status = "pending"
        out_steps.append({**step, "status": status})
    return {
        "currentIndex": current_index,
        "steps": out_steps,
        "label": label,
    }


def mark_step_done(
    steps: list[dict[str, Any]],
    step_id: str,
    *,
    duration_ms: int | None = None,
    detail: str | None = None,
) -> None:
    for step in steps:
        if step.get("id") == step_id:
            if duration_ms is not None:
                step["durationMs"] = duration_ms
            if detail:
                step["detail"] = detail
            return


async def set_run_progress(
    session: object,
    run_id: str,
    steps: list[dict[str, Any]],
    current_index: int,
    label: str,
    *,
    force: bool = False,
    event_type: str | None = None,
) -> None:
    """Publish live progress over SSE; persist to DB on an interval (or when forced)."""
    from sqlalchemy.ext.asyncio import AsyncSession

    progress = progress_snapshot(steps, current_index, label)
    if event_type:
        progress["lastEvent"] = event_type
        progress["eventVersion"] = 1

    from audit_workbench.services.run_events import publish_run_progress

    await publish_run_progress(run_id, progress)

    settings = get_settings()
    interval_s = settings.progress_commit_interval_ms / 1000.0
    now = time.monotonic()
    last = _last_progress_commit.get(run_id, 0.0)
    if not force and (now - last) < interval_s:
        return

    if isinstance(session, AsyncSession):
        run = await session.get(Run, run_id)
        if run:
            run.progress = progress
        _touch_progress_cache(run_id, now)
        return

    from audit_workbench.db.base import async_session_factory

    async with async_session_factory() as progress_session:
        run = await progress_session.get(Run, run_id)
        if not run:
            return
        run.progress = progress
        await progress_session.commit()
    _touch_progress_cache(run_id, now)


async def init_queued_progress(session: object, run_id: str) -> None:
    steps = [
        _step(
            "queue",
            "Queued for worker",
            detail=_queue_wait_detail(),
        )
    ]
    await set_run_progress(session, run_id, steps, 0, "Waiting for worker\u2026", force=True)


async def fail_run_progress(run_id: str, error: str) -> None:
    """Publish a terminal failed progress snapshot (queue step failed)."""
    detail = error[:500]
    steps = [
        _step(
            "queue",
            "Run failed",
            status="done",
            detail=detail,
        )
    ]
    progress = {
        "currentIndex": 0,
        "steps": steps,
        "label": detail,
        "failed": True,
    }

    from audit_workbench.services.run_events import publish_run_progress

    await publish_run_progress(run_id, progress)

    from audit_workbench.services.run_events import publish_run_terminal

    await publish_run_terminal(run_id, status="failed")

    from audit_workbench.db.base import async_session_factory

    async with async_session_factory() as session:
        run = await session.get(Run, run_id)
        if run:
            run.progress = progress
            await session.commit()
    clear_progress_commit_cache(run_id)
