"""Taskiq entry points, one image for both roles:

    taskiq worker repody.worker:broker --workers 1 --max-async-tasks $AUDIT_WORKER_CONCURRENCY
    taskiq scheduler repody.worker:scheduler      # exactly one replica

Workers run the runs and the scheduled maintenance; scale them with replicas.
"""

from taskiq import TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.schedule_sources import LabelScheduleSource

from repody.app import maintenance
from repody.app.execute import process_run
from repody.extraction import client
from repody.infra import db, observability
from repody.infra.queue import TASK_NAME, broker
from repody.infra.redis import close_redis
from repody.settings import get_settings

__all__ = ["broker", "scheduler"]

MAINTENANCE_TASK = "maintenance"


@broker.on_event(TaskiqEvents.WORKER_STARTUP, TaskiqEvents.CLIENT_STARTUP)
async def _startup(_state: TaskiqState) -> None:
    """Logging and error reporting for the worker and the scheduler (a broker client)."""
    observability.setup()


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _shutdown(_state: TaskiqState) -> None:
    await client.close()
    await close_redis()
    await db.engine.dispose()


broker.register_task(process_run, task_name=TASK_NAME)
broker.register_task(
    maintenance.upkeep,
    task_name=MAINTENANCE_TASK,
    schedule=[{"interval": get_settings().maintenance_interval_seconds}],
)

# Sends each task whose `schedule` label is due (here: maintenance) to the queue.
scheduler = TaskiqScheduler(broker, sources=[LabelScheduleSource(broker)])
