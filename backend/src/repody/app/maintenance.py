"""Periodic upkeep, the Hatchet ``maintenance`` cron (repody.worker): delete runs past their
retention, and declined access requests past theirs. Stuck runs need no sweep: Hatchet's
timeouts fail them (repody.app.execute.fail_unfinished)."""

import structlog

from repody.app.access import purge_declined
from repody.app.runs import purge_expired
from repody.infra import db

log = structlog.get_logger(__name__)


async def upkeep() -> None:
    purged = await purge_expired()
    async with db.session_factory() as session:
        declined = await purge_declined(session)
        await session.commit()
    if purged or declined:
        log.info("maintenance", runs_purged=purged, declined_requests_purged=declined)
