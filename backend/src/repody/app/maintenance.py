"""Periodic upkeep: fail runs that are stuck, resend tasks that were never sent, and delete runs
past their retention (and, in the playground, visitors' old workflows).

The Taskiq scheduler (`taskiq scheduler repody.worker:scheduler`, one replica) sends the
`maintenance` task every AUDIT_MAINTENANCE_INTERVAL_SECONDS; one worker runs it each time."""

from datetime import UTC, datetime

import structlog

from repody.app.lifecycle import failure, move_runs, stuck_queued, stuck_running
from repody.app.runs import purge_expired
from repody.app.workflows import purge_visitor_workflows
from repody.infra import db, queue

log = structlog.get_logger(__name__)


async def fail_stuck_runs() -> list[str]:
    """Fail running runs that lost their worker and queued runs that will not start: one
    conditional UPDATE each, so a run a worker finishes meanwhile is left alone."""
    now = datetime.now(UTC)
    async with db.session_factory() as session:
        lost = await move_runs(
            session,
            "failed",
            stuck_running(now),
            only_from="running",
            **failure("The worker stopped before the run finished."),
        )
        expired = await move_runs(
            session,
            "failed",
            stuck_queued(now),
            only_from="queued",
            **failure("The run waited over an hour for a worker."),
        )
        await session.commit()
    return lost + expired


async def upkeep() -> None:
    """One maintenance pass (a scheduled Taskiq task: one worker runs it per interval)."""
    failed = await fail_stuck_runs()
    resent = await queue.redispatch_lost()
    purged = await purge_expired()
    async with db.session_factory() as session:
        visitors = await purge_visitor_workflows(session)
        await session.commit()
    if failed or resent or purged or visitors:
        log.info(
            "maintenance",
            runs_failed=failed,
            runs_resent=resent,
            runs_purged=purged,
            visitor_workflows_purged=visitors,
        )
