"""Queue depth admission control and queue position for waiting runs."""

from __future__ import annotations

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Run, RunStatus
from audit_workbench.services.run_pool_classifier import predict_worker_pool
from audit_workbench.settings import get_settings

log = structlog.get_logger(__name__)

_INFLIGHT = (RunStatus.queued.value, RunStatus.running.value)


class QueueCapacityExceeded(Exception):
    def __init__(
        self,
        *,
        scope: str,
        limit: int,
        current: int,
        retry_after_seconds: int = 60,
    ) -> None:
        self.scope = scope
        self.limit = limit
        self.current = current
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            f"Audit queue at capacity ({scope}): {current} active, limit {limit}. "
            "Try again in a minute."
        )


async def count_queued(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Run).where(Run.status == RunStatus.queued.value)
        )
        or 0
    )


async def count_inflight(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Run).where(Run.status.in_(_INFLIGHT))
        )
        or 0
    )


async def count_ocr_inflight(session: AsyncSession) -> int:
    """Inflight runs classified for the OCR/document-model worker pool."""
    result = await session.execute(
        select(Run.id).where(
            Run.status.in_(_INFLIGHT),
            Run.worker_pool == "ocr",
        )
    )
    return len(list(result.scalars()))


async def queue_position(session: AsyncSession, run_id: str) -> tuple[int | None, int | None]:
    """1-based position among queued runs and total queued depth."""
    run = await session.get(Run, run_id)
    if not run or run.status != RunStatus.queued.value:
        return None, None

    result = await session.execute(
        select(Run.id)
        .where(Run.status == RunStatus.queued.value)
        .order_by(Run.created_at.asc(), Run.id.asc())
    )
    ids = list(result.scalars())
    depth = len(ids)
    if depth == 0 or run_id not in ids:
        return None, None
    return ids.index(run_id) + 1, depth


def _queue_label(position: int, depth: int) -> str:
    if depth <= 1:
        return "Waiting for worker…"
    return f"Queued — position {position} of {depth}"


def _queue_detail(position: int, depth: int) -> str:
    ahead = max(0, position - 1)
    if ahead == 0:
        return "Next in line for a worker slot."
    if ahead == 1:
        return "1 run ahead of you in the queue."
    return f"{ahead} runs ahead of you in the queue."


def apply_queue_meta(progress: dict, *, position: int, depth: int) -> dict:
    """Merge queue position fields into a progress payload."""
    updated = dict(progress)
    updated["queuePosition"] = position
    updated["queueDepth"] = depth
    updated["label"] = _queue_label(position, depth)
    steps = list(updated.get("steps") or [])
    if steps and steps[0].get("id") == "queue":
        step0 = dict(steps[0])
        step0["detail"] = _queue_detail(position, depth)
        step0["status"] = "active" if position == 1 else "pending"
        steps[0] = step0
    updated["steps"] = steps
    return updated


async def check_admission(
    session: AsyncSession,
    *,
    workflow_id: str,
    file_bindings: list | None = None,
) -> str:
    """
    Reject new runs when queue/inflight limits are exceeded.
    Returns predicted worker pool when admitted.
    """
    settings = get_settings()
    if not settings.admission_control_enabled or settings.run_jobs_inline:
        return await predict_worker_pool(session, workflow_id, file_bindings=file_bindings)

    pool = await predict_worker_pool(session, workflow_id, file_bindings=file_bindings)
    queued = await count_queued(session)
    inflight = await count_inflight(session)
    ocr_inflight = await count_ocr_inflight(session)

    if queued >= settings.admission_max_queued:
        log.warning(
            "admission_queued_limit",
            event_domain="admission",
            queued=queued,
            limit=settings.admission_max_queued,
        )
        raise QueueCapacityExceeded(
            scope="queued",
            limit=settings.admission_max_queued,
            current=queued,
            retry_after_seconds=settings.admission_retry_after_seconds,
        )

    if inflight >= settings.admission_max_inflight:
        log.warning(
            "admission_inflight_limit",
            event_domain="admission",
            inflight=inflight,
            limit=settings.admission_max_inflight,
        )
        raise QueueCapacityExceeded(
            scope="inflight",
            limit=settings.admission_max_inflight,
            current=inflight,
            retry_after_seconds=settings.admission_retry_after_seconds,
        )

    if pool == "ocr" and ocr_inflight >= settings.admission_max_ocr_inflight:
        log.warning(
            "admission_ocr_limit",
            event_domain="admission",
            ocr_inflight=ocr_inflight,
            limit=settings.admission_max_ocr_inflight,
        )
        raise QueueCapacityExceeded(
            scope="ocr",
            limit=settings.admission_max_ocr_inflight,
            current=ocr_inflight,
            retry_after_seconds=settings.admission_retry_after_seconds,
        )

    return pool


async def init_queued_progress_with_position(session: AsyncSession, run_id: str) -> None:
    from audit_workbench.services.run_progress import init_queued_progress

    await init_queued_progress(session, run_id)
    run = await session.get(Run, run_id)
    if not run or not run.progress:
        return
    position, depth = await queue_position(session, run_id)
    if position is None or depth is None:
        return
    run.progress = apply_queue_meta(run.progress, position=position, depth=depth)


async def refresh_queued_positions(session: AsyncSession) -> int:
    """Update queue position metadata for all queued runs (DB + SSE)."""
    from audit_workbench.services.run_events import publish_run_progress

    result = await session.execute(
        select(Run)
        .where(Run.status == RunStatus.queued.value)
        .order_by(Run.created_at.asc(), Run.id.asc())
    )
    runs = list(result.scalars())
    depth = len(runs)
    if depth == 0:
        return 0

    updated = 0
    for index, run in enumerate(runs, start=1):
        if not run.progress:
            continue
        progress = apply_queue_meta(run.progress, position=index, depth=depth)
        if progress == run.progress:
            continue
        run.progress = progress
        updated += 1
        await publish_run_progress(run.id, progress)
    if updated:
        await session.flush()
    return updated


async def enrich_progress_for_poll(session: AsyncSession, run: Run) -> dict | None:
    """Refresh queue position on poll while the run is still queued."""
    if not run.progress:
        return None
    if run.status != RunStatus.queued.value:
        return run.progress
    position, depth = await queue_position(session, run.id)
    if position is None or depth is None:
        return run.progress
    progress = apply_queue_meta(run.progress, position=position, depth=depth)
    if progress != run.progress:
        run.progress = progress
        await session.flush()
    return progress
