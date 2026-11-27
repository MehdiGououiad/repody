"""The Hatchet worker: runs the runs and the maintenance cron (`python -m repody.worker`).

- ``process-run`` processes one run. Hatchet bounds it: it waits at most QUEUE_TIMEOUT for a
  worker and runs at most AUDIT_RUN_TIMEOUT_MINUTES; each client (API key or user) starts at
  most AUDIT_RUNS_PER_MINUTE_PER_CLIENT a minute (a dynamic rate limit: more wait their turn)
  and has at most AUDIT_RUNS_IN_PROGRESS_PER_CLIENT in progress, clients taking turns (round
  robin), so one bulk upload cannot hold every worker slot.
  When Hatchet gives up on it (a timeout, a cancellation), the failure task fails the run in our
  database. A task whose worker died is given to another worker, which starts the run over
  (repody.app.execute._claim).
- ``maintenance`` runs every minute (a Hatchet cron): it fails runs the queue lost, deletes runs
  past their retention and declined access requests past theirs.

The worker takes AUDIT_WORKER_CONCURRENCY runs at a time (Hatchet slots); scale it with replicas.
The client's connection comes from the HATCHET_CLIENT_* environment.
"""

from collections.abc import AsyncGenerator
from datetime import timedelta

from hatchet_sdk import (
    ConcurrencyExpression,
    ConcurrencyLimitStrategy,
    Context,
    DesiredWorkerLabel,
    EmptyModel,
    RateLimit,
    RateLimitDuration,
)
from pydantic import BaseModel

from repody.app import maintenance
from repody.app.execute import fail_unfinished, process_run
from repody.app.lifecycle import QUEUE_TIMEOUT
from repody.app.stage import execute_idp_stage
from repody.extraction import client
from repody.infra import db, observability
from repody.infra.queue import IDP_STAGE_WORKFLOW, MAINTENANCE_WORKFLOW, RUN_WORKFLOW, hatchet
from repody.schemas.stage import IdpStageInput, IdpStageOutput
from repody.settings import get_settings


class RunInput(BaseModel):
    run_id: str
    client_key: str


settings = get_settings()

runs = hatchet().workflow(
    name=RUN_WORKFLOW,
    input_validator=RunInput,
    concurrency=ConcurrencyExpression(
        expression="input.client_key",
        max_runs=settings.runs_in_progress_per_client,
        limit_strategy=ConcurrencyLimitStrategy.GROUP_ROUND_ROBIN,
    ),
)


@runs.task(
    execution_timeout=timedelta(minutes=settings.run_timeout_minutes),
    schedule_timeout=QUEUE_TIMEOUT,
    # Retried after 3, 9 and 27 s (backoff_factor ** retry, docs.hatchet.run/v1/retry-policies)
    # when the task raises, which only an unreachable database does (process_run fails the run
    # for any other error), or when it times out (docs.hatchet.run/v1/timeouts). A retry starts
    # the run over; one past the run's time limit fails it instead (repody.app.execute._claim).
    retries=3,
    backoff_factor=3.0,
    backoff_max_seconds=60,
    rate_limits=[
        RateLimit(
            dynamic_key="input.client_key",
            units=1,
            limit=settings.runs_per_minute_per_client,
            duration=RateLimitDuration.MINUTE,
        )
    ]
    if settings.runs_per_minute_per_client
    else None,
)
async def process(input: RunInput, _ctx: Context) -> None:
    await process_run(input.run_id)


@runs.on_failure_task()
async def failed(input: RunInput, _ctx: Context) -> None:
    await fail_unfinished(input.run_id)


# A cron tick while the previous pass still runs is dropped (CANCEL_NEWEST on one static key):
# passes never pile up on the worker's slots, which the runs share.
upkeep = hatchet().workflow(
    name=MAINTENANCE_WORKFLOW,
    on_crons=["* * * * *"],
    concurrency=ConcurrencyExpression(
        expression="'maintenance'",
        max_runs=1,
        limit_strategy=ConcurrencyLimitStrategy.CANCEL_NEWEST,
    ),
)


@upkeep.task(execution_timeout=timedelta(minutes=5))
async def maintain(_input: EmptyModel, _ctx: Context) -> None:
    await maintenance.upkeep()


@hatchet().task(
    name=IDP_STAGE_WORKFLOW,
    input_validator=IdpStageInput,
    execution_timeout=timedelta(minutes=settings.run_timeout_minutes),
    schedule_timeout=QUEUE_TIMEOUT,
    retries=3,
    backoff_factor=3.0,
    backoff_max_seconds=60,
    desired_worker_labels=[DesiredWorkerLabel(key="pool", value="idp", required=True)],
)
async def extract_and_validate(input: IdpStageInput, _ctx: Context) -> IdpStageOutput:
    """Process an IDP stage invoked by ``repody-core`` over Hatchet."""
    return await execute_idp_stage(input)


async def lifespan() -> AsyncGenerator[None]:
    """Logging and error reporting at start; the model client and database pool at stop."""
    observability.setup()
    yield
    await client.close()
    await db.engine.dispose()


def main() -> None:
    worker = hatchet().worker(
        "repody-worker",
        slots=settings.worker_concurrency,
        labels={"pool": "idp"},
        workflows=[runs, upkeep, extract_and_validate],
        lifespan=lifespan,
    )
    worker.start()


if __name__ == "__main__":
    main()
