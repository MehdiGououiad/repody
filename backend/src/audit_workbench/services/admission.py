"""Queue depth counters for dashboard / health (no HTTP admission caps)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Run, RunStatus

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
