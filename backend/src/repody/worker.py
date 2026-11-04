"""Taskiq worker entry point:

    taskiq worker repody.worker:broker --workers 1 --max-async-tasks $AUDIT_WORKER_CONCURRENCY

One process per container; scale with replicas.
"""

from __future__ import annotations

from taskiq import TaskiqEvents, TaskiqState

from repody import observability
from repody.app.execute import process_run
from repody.queue import TASK_NAME, broker

__all__ = ["broker"]


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _startup(_state: TaskiqState) -> None:
    observability.setup()


@broker.task(task_name=TASK_NAME)
async def process_run_task(run_id: str) -> None:
    await process_run(run_id)
