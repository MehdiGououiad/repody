"""The run queue: one Taskiq task, ``process_run``, on a Redis stream.

The API commits a run, then sends its task and stamps ``runs.dispatched_at``. When the send
fails, maintenance sends it again. Redis Streams redeliver unacknowledged tasks, and the
worker's claim is conditional, so a duplicate delivery does nothing.

Acknowledged messages stay in a Redis stream until it is trimmed, so the stream is capped
(``maxlen``, approximate trimming) far above the queue limit: only old, acknowledged messages
are ever dropped. A message is redelivered once it has been unacknowledged for longer than a
run may take (``idle_timeout``), so a run still in progress is not delivered twice.

Tracing: the OpenTelemetry agent (`opentelemetry-instrument`) loads Taskiq's own instrumentor
(`taskiq.instrumentation.TaskiqInstrumentor`), which adds the tracing middleware to the broker;
adding it here as well would trace every task twice.
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from taskiq.kicker import AsyncKicker
from taskiq_redis import RedisStreamBroker

from repody.infra import db
from repody.infra.models import Run
from repody.settings import get_settings

log = structlog.get_logger(__name__)

TASK_NAME = "process_run"
STREAM_MAXLEN = 10_000

_settings = get_settings()
broker = RedisStreamBroker(
    url=_settings.redis_url.get_secret_value(),
    queue_name="repody:runs",
    maxlen=max(STREAM_MAXLEN, _settings.max_queued_runs * 10),
    idle_timeout=(_settings.run_timeout_minutes + 1) * 60_000,
)


async def dispatch(run_id: str) -> bool:
    """Send the run's task and stamp it sent; False (logged) when either fails.

    Maintenance sends a run again while it has no stamp; a duplicate send is harmless (the
    worker's claim is conditional), so a failed stamp only means one more delivery.
    """
    try:
        await AsyncKicker(TASK_NAME, broker, labels={}).kiq(run_id)
        async with db.session_factory() as session:
            await session.execute(
                update(Run).where(Run.id == run_id).values(dispatched_at=datetime.now(UTC))
            )
            await session.commit()
    except Exception as exc:
        log.warning("run_dispatch_failed", run_id=run_id, error=repr(exc))
        return False
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
