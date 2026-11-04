"""The run queue: one Taskiq task, ``process_run``, on a Redis stream.

The API commits a run, then sends its task and stamps ``runs.dispatched_at``. When the send
fails, maintenance sends it again. Redis Streams redeliver unacknowledged tasks, and the
worker's claim is conditional, so a duplicate delivery does nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from taskiq.kicker import AsyncKicker
from taskiq.middlewares.opentelemetry_middleware import OpenTelemetryMiddleware
from taskiq_redis import RedisStreamBroker

from repody import db
from repody.models import Run
from repody.settings import get_settings

log = structlog.get_logger(__name__)

TASK_NAME = "process_run"
broker = RedisStreamBroker(url=get_settings().redis_url, queue_name="repody:runs").with_middlewares(
    OpenTelemetryMiddleware()
)


async def dispatch(run_id: str) -> bool:
    """Send the run's task; False (logged, retried by maintenance) when Redis refuses it."""
    try:
        await AsyncKicker(TASK_NAME, broker, labels={}).kiq(run_id)
    except Exception as exc:
        log.warning("run_dispatch_failed", run_id=run_id, error=repr(exc))
        return False
    async with db.session_factory() as session:
        await session.execute(
            update(Run).where(Run.id == run_id).values(dispatched_at=datetime.now(UTC))
        )
        await session.commit()
    return True


async def redispatch_lost() -> int:
    """Send again the queued runs whose first send failed (older than 30 s)."""
    async with db.session_factory() as session:
        run_ids = await session.scalars(
            select(Run.id)
            .where(
                Run.status == "queued",
                Run.dispatched_at.is_(None),
                Run.created_at < datetime.now(UTC) - timedelta(seconds=30),
            )
            .limit(100)
        )
        pending = list(run_ids)
    return sum([await dispatch(run_id) for run_id in pending])
