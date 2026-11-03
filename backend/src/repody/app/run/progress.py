from __future__ import annotations

import time
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.run.snapshot import SnapshotDocument
from repody.app.run.sse import publish_run_progress, publish_run_terminal
from repody.extraction.types import ExtractionMetadata
from repody.inference.runtime import is_serverless_inference
from repody.infra.db import base as db_base
from repody.infra.db.models import Run
from repody.rules.conditions import logic_check_entries
from repody.settings import get_settings

StepStatus = Literal["pending", "active", "done"]


_last_progress_commit: dict[str, float] = {}
_MAX_PROGRESS_CACHE = 512

__all__ = [
    "StepStatus",
    "build_run_progress_plan",
    "clear_progress_commit_cache",
    "completed_extraction_detail",
    "document_wants_extraction",
    "fail_run_progress",
    "init_queued_progress",
    "mark_step_done",
    "progress_snapshot",
    "progress_step",
    "set_run_progress",
    "step_index_for",
]


def step_index_for(steps: list[dict[str, Any]], step_id: str) -> int | None:
    """Return the plan index for ``step_id``, or None if missing."""
    for index, step in enumerate(steps):
        if step.get("id") == step_id:
            return index
    return None


def progress_step(
    step_id: str,
    label: str,
    *,
    status: StepStatus = "pending",
    mode: str | None = None,
    kind: str | None = None,
    detail: str | None = None,
    duration_ms: int | None = None,
    gpu_cold_start_hint: bool = False,
) -> dict[str, Any]:
    row: dict[str, Any] = {"id": step_id, "label": label, "status": status}
    if mode:
        row["mode"] = mode
    if kind:
        row["kind"] = kind
    if detail:
        row["detail"] = detail
    if duration_ms is not None:
        row["durationMs"] = duration_ms
    if gpu_cold_start_hint:
        row["gpuColdStartHint"] = True
    return row


def _queue_wait_detail() -> str:
    if is_serverless_inference():
        return (
            "Waiting for a worker slot. Serverless GPU extraction can take 1-2 minutes "
            "on the first request after the GPU has been idle."
        )
    return (
        "Waiting for a worker slot - if another document is processing, "
        "this can take several minutes on CPU"
    )


def document_wants_extraction(doc: SnapshotDocument) -> bool:
    """A document with a file goes to the model when it has schema fields or wants Markdown."""
    return doc.markdown_extraction or any(f.name.strip() for f in doc.schema_fields)


def completed_extraction_detail(meta: ExtractionMetadata) -> str:
    parts: list[str] = []
    if meta.cache_hit:
        parts.append("Same document as a previous run — reused the cached extraction")
    if meta.gpu_cold_start_likely:
        parts.append("Slow extraction may include GPU warm-up (first request after idle)")
    if meta.pages_dropped and meta.pages_rendered:
        parts.append(
            f"Warning: only {meta.pages_sent} of {meta.pages_rendered} page(s) sent to the model"
        )
    parts.append(f"{meta.fields_extracted} field(s) in {meta.extraction_ms}ms")
    return " · ".join(parts)


def build_run_progress_plan(
    *,
    workflow_docs: list[SnapshotDocument],
    rules: list[dict],
    docs_with_files: set[str],
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        progress_step(
            "queue",
            "Queued for worker",
            detail=_queue_wait_detail(),
        ),
    ]
    for doc in workflow_docs:
        if doc.id not in docs_with_files or not document_wants_extraction(doc):
            continue
        steps.append(
            progress_step(
                f"extract-{doc.id}",
                f"Extract · {doc.document_type or 'Document'}",
                mode="document_model",
            )
        )
    for rule in rules:
        checks = logic_check_entries(rule)
        if not checks:
            rule_id = rule.get("id") or "rule"
            name = rule.get("name") or "Rule"
            steps.append(
                progress_step(
                    f"rule-{rule_id}",
                    f"Validate \u00b7 {name}",
                    kind="logic",
                    detail="Logic expression on extracted fields",
                )
            )
            continue
        for check in checks:
            check_id = check.get("id") or "rule"
            name = check.get("name") or "Check"
            expr = (check.get("body") or "").strip()
            steps.append(
                progress_step(
                    f"rule-{check_id}",
                    f"Validate \u00b7 {name}",
                    kind="logic",
                    detail=f"Expression: {expr}" if expr else "Logic check on extracted fields",
                )
            )
    steps.append(
        progress_step("finalize", "Build audit report", detail="Persist fields and rule results")
    )
    return steps


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
    cache_hit: bool = False,
) -> None:
    for step in steps:
        if step.get("id") == step_id:
            if duration_ms is not None:
                step["durationMs"] = duration_ms
            if detail:
                step["detail"] = detail
            if cache_hit:
                step["cacheHit"] = True
            return


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
    progress = progress_snapshot(steps, current_index, label)
    if event_type:
        progress["lastEvent"] = event_type
        progress["eventVersion"] = 1

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

    async with db_base.async_session_factory() as progress_session:
        run = await progress_session.get(Run, run_id)
        if not run:
            return
        run.progress = progress
        await progress_session.commit()
    _touch_progress_cache(run_id, now)


async def init_queued_progress(session: object, run_id: str) -> None:
    steps = [
        progress_step(
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
        progress_step(
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

    await publish_run_progress(run_id, progress)

    await publish_run_terminal(run_id, status="failed")

    async with db_base.async_session_factory() as session:
        run = await session.get(Run, run_id)
        if run:
            run.progress = progress
            await session.commit()
    clear_progress_commit_cache(run_id)
