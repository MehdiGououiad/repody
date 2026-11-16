"""The run queue: Hatchet (https://docs.hatchet.run).

The API commits a run, then triggers the ``process-run`` workflow with its id (``dispatch``),
and keeps the Hatchet run id to cancel it (``cancel``). Hatchet stores the trigger durably, gives
the run to a worker (``repody.worker``), enforces its timeouts and rate limit, and reports a
failure (a timeout, a lost worker, an error) to the workflow's failure task, which fails the run
in our database. The client reads its settings from the ``HATCHET_CLIENT_*`` environment.
"""

from functools import cache

import structlog
from hatchet_sdk import Hatchet

log = structlog.get_logger(__name__)

RUN_WORKFLOW = "process-run"
MAINTENANCE_WORKFLOW = "maintenance"


@cache
def hatchet() -> Hatchet:
    """The process's Hatchet client (created on first use: it needs HATCHET_CLIENT_TOKEN)."""
    return Hatchet()


async def dispatch(run_id: str, client_key: str) -> str:
    """Queue the run; the Hatchet run id. ``client_key`` keys the per-client rate limit."""
    details = await hatchet().runs.aio_create(
        workflow_name=RUN_WORKFLOW,
        input={"run_id": run_id, "client_key": client_key},
        additional_metadata={"run_id": run_id},
    )
    return details.run.metadata.id


async def cancel(task_run_id: str) -> None:
    """Stop the run's Hatchet task; a failure is logged (the run is already failed in our
    database, and its worker cannot finish it then)."""
    try:
        await hatchet().runs.aio_cancel(task_run_id)
    except Exception as exc:
        log.warning("run_cancel_failed", task_run_id=task_run_id, error=repr(exc))
