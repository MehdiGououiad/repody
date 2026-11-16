"""Periodic upkeep, the Hatchet ``maintenance`` cron (repody.worker): delete runs past their
retention and, in the playground, visitors' old workflows. Stuck runs need no sweep: Hatchet's
timeouts fail them (repody.app.execute.fail_unfinished)."""

import structlog

from repody.app.runs import purge_expired
from repody.app.workflows import purge_visitor_workflows
from repody.infra import db

log = structlog.get_logger(__name__)


async def upkeep() -> None:
    purged = await purge_expired()
    async with db.session_factory() as session:
        visitors = await purge_visitor_workflows(session)
        await session.commit()
    if purged or visitors:
        log.info("maintenance", runs_purged=purged, visitor_workflows_purged=visitors)
