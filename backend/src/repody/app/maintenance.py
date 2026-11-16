"""Periodic upkeep, the Hatchet ``maintenance`` cron (repody.worker): delete runs past their
retention. Stuck runs need no sweep: Hatchet's timeouts fail them
(repody.app.execute.fail_unfinished)."""

import structlog

from repody.app.runs import purge_expired

log = structlog.get_logger(__name__)


async def upkeep() -> None:
    if purged := await purge_expired():
        log.info("maintenance", runs_purged=purged)
