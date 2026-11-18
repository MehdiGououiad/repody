"""Periodic upkeep, the Hatchet ``maintenance`` cron (repody.worker): fail the runs the queue lost
(Hatchet's timeouts fail the others, repody.app.execute.fail_unfinished), delete runs past their
retention, and declined access requests past theirs."""

import structlog

from repody.app.access import purge_declined
from repody.app.lifecycle import fail_stuck
from repody.app.runs import purge_expired
from repody.infra import db

log = structlog.get_logger(__name__)


async def upkeep() -> None:
    stuck = await fail_stuck()
    purged = await purge_expired()
    async with db.session_factory() as session:
        declined = await purge_declined(session)
        await session.commit()
    if stuck or purged or declined:
        log.info(
            "maintenance",
            stuck_runs_failed=stuck,
            runs_purged=purged,
            declined_requests_purged=declined,
        )
