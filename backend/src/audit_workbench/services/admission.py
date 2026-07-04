"""Queue depth admission control."""

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


async def count_ocr_inflight(session: AsyncSession) -> int:
    """Inflight runs classified for the OCR/document-model worker pool."""
    return int(
        await session.scalar(
            select(func.count())
            .select_from(Run)
            .where(
                Run.status.in_(_INFLIGHT),
                Run.worker_pool == "ocr",
            )
        )
        or 0
    )


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
    if not settings.admission_control_enabled:
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
