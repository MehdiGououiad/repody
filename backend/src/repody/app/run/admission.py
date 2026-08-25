"""Queue depth counters and HTTP admission caps for enqueue."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.db.models import Run, RunStatus
from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.settings import get_settings

_INFLIGHT = (RunStatus.queued.value, RunStatus.running.value)


async def count_queued(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Run).where(Run.status == RunStatus.queued.value)
        )
        or 0
    )


async def count_inflight(session: AsyncSession) -> int:
    return int(
        await session.scalar(select(func.count()).select_from(Run).where(Run.status.in_(_INFLIGHT)))
        or 0
    )


async def count_running(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count()).select_from(Run).where(Run.status == RunStatus.running.value)
        )
        or 0
    )


async def count_extract_inflight(session: AsyncSession) -> int:
    """Inflight runs classified for the document-model worker pool."""
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Run)
            .where(
                Run.status.in_(_INFLIGHT),
                Run.worker_pool == "extract",
            )
        )
        or 0
    )


async def _admission_counts(session: AsyncSession) -> tuple[int, int, int]:
    """One round-trip: queued, inflight, extract-inflight (FILTER aggregates)."""
    row = (
        await session.execute(
            select(
                func.count().filter(Run.status == RunStatus.queued.value),
                func.count(),
                func.count().filter(Run.worker_pool == "extract"),
            ).where(Run.status.in_(_INFLIGHT))
        )
    ).one()
    return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)


async def queue_snapshot_counts(session: AsyncSession) -> tuple[int, int, int]:
    """Return (queued, running, inflight) in one round-trip."""
    row = (
        await session.execute(
            select(
                func.count().filter(Run.status == RunStatus.queued.value),
                func.count().filter(Run.status == RunStatus.running.value),
                func.count(),
            ).where(Run.status.in_(_INFLIGHT))
        )
    ).one()
    return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)


async def check_admission(
    session: AsyncSession,
    *,
    predicted_pool: str,
) -> Result[None]:
    """Fail closed with CAPACITY when queue/inflight caps are exceeded (0 = disabled)."""
    settings = get_settings()
    retry_after = max(1, int(settings.admission_retry_after_seconds))

    max_queued = int(settings.admission_max_queued)
    max_inflight = int(settings.admission_max_inflight)
    max_extract = int(settings.admission_max_extract_inflight)
    need_extract = max_extract > 0 and predicted_pool == "extract"

    if max_queued <= 0 and max_inflight <= 0 and not need_extract:
        return Result.ok(None)

    queued, inflight, extract_n = await _admission_counts(session)

    if max_queued > 0 and queued >= max_queued:
        return Result.fail(
            AppError(
                code=ErrorCode.CAPACITY,
                message=(
                    f"Queue is full ({queued}/{max_queued} queued runs). Retry after workers drain."
                ),
                retry_after_seconds=retry_after,
            )
        )

    if max_inflight > 0 and inflight >= max_inflight:
        return Result.fail(
            AppError(
                code=ErrorCode.CAPACITY,
                message=(
                    f"Platform at capacity ({inflight}/{max_inflight} inflight runs). "
                    "Retry shortly."
                ),
                retry_after_seconds=retry_after,
            )
        )

    if need_extract and extract_n >= max_extract:
        return Result.fail(
            AppError(
                code=ErrorCode.CAPACITY,
                message=(
                    f"Extract pool at capacity ({extract_n}/{max_extract} inflight). "
                    "Retry when document-model workers free up."
                ),
                retry_after_seconds=retry_after,
            )
        )

    return Result.ok(None)
