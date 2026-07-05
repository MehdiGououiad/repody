from __future__ import annotations

from collections.abc import Sequence

import structlog

from audit_workbench.db.models.enums import RunStatus
from audit_workbench.services.run.domain.events import (
    RunCompleted,
    RunDomainEvent,
    RunFailed,
    RunQueued,
    RunStarted,
)
from audit_workbench.services.run.progress_persist import fail_run_progress

log = structlog.get_logger(__name__)


async def _on_run_started(event: RunStarted) -> None:
    from audit_workbench.db.base import async_session_factory
    from audit_workbench.services.queue import refresh_queued_positions

    async with async_session_factory() as session:
        await refresh_queued_positions(session)
        await session.commit()
    log.info(
        "run_started",
        event_domain="audit_run",
        run_id=event.run_id,
        workflow_id=event.workflow_id,
    )


async def _on_run_completed(event: RunCompleted) -> None:
    from audit_workbench.services.run_events import publish_run_terminal

    await publish_run_terminal(event.run_id, status=RunStatus.done.value)
    log.info(
        "run_completed",
        event_domain="audit_run",
        run_id=event.run_id,
        overall_status=event.overall_status,
        summary_total=event.summary_total,
        summary_failed=event.summary_failed,
    )


async def _on_run_failed(event: RunFailed) -> None:
    await fail_run_progress(event.run_id, event.error)
    log.warning(
        "run_failed_terminal",
        event_domain="audit_run",
        run_id=event.run_id,
        previous_status=event.previous_status,
        error=event.error[:200],
    )


async def _on_run_queued(_event: RunQueued) -> None:
    """Enqueue orchestration owns RunQueued side effects today."""


class RunDomainEventPublisher:
    """Adapter — publishes domain events to queue refresh, SSE, and progress infrastructure."""

    async def publish(self, events: Sequence[RunDomainEvent]) -> None:
        for event in events:
            if isinstance(event, RunQueued):
                await _on_run_queued(event)
            elif isinstance(event, RunStarted):
                await _on_run_started(event)
            elif isinstance(event, RunCompleted):
                await _on_run_completed(event)
            elif isinstance(event, RunFailed):
                await _on_run_failed(event)
            else:
                raise TypeError(f"Unhandled run domain event: {type(event)!r}")
