"""Hatchet durable orchestrator worker for ``repody_core`` (``pool=core``)."""

from datetime import timedelta
from typing import Any

from hatchet_sdk import (
    DesiredWorkerLabel,
    DurableContext,
    Hatchet,
    SleepCondition,
    UserEventCondition,
    or_,
)
from hatchet_sdk.runnables.workflow import Standalone

from repody_core.app.pipelines import execute_pipeline_stages
from repody_core.infra.queue import (
    APPROVAL_DECIDED_EVENT,
    PIPELINE_WORKFLOW,
    HatchetStageInvoker,
    hatchet,
)
from repody_core.schemas.pipelines import PipelineTaskInput
from repody_core.settings import get_settings


def build_pipeline_workflow(client: Hatchet) -> Standalone[PipelineTaskInput, dict[str, Any]]:
    """Register the durable pipeline workflow with zero-slot HITL event waits."""
    settings = get_settings()
    invoker = HatchetStageInvoker(client)

    @client.durable_task(
        name=PIPELINE_WORKFLOW,
        input_validator=PipelineTaskInput,
        execution_timeout=timedelta(hours=settings.approval_sla_hours + 1),
        schedule_timeout=timedelta(hours=1),
        desired_worker_labels=[
            DesiredWorkerLabel(key="pool", value="core", required=True),
        ],
    )
    async def execute_pipeline(input: PipelineTaskInput, ctx: DurableContext) -> dict[str, Any]:
        async def wait_for_approval(approval_id: str) -> dict[str, Any]:
            consider_since = await ctx.aio_now() - timedelta(minutes=5)
            return await ctx.aio_wait_for(
                "four-eyes-approval",
                or_(
                    SleepCondition(timedelta(hours=settings.approval_sla_hours)),
                    UserEventCondition(
                        event_key=APPROVAL_DECIDED_EVENT,
                        scope=approval_id,
                        consider_events_since=consider_since,
                    ),
                ),
            )

        return await execute_pipeline_stages(
            input,
            invoker=invoker,
            wait_for_approval=wait_for_approval,
        )

    return execute_pipeline


def main() -> None:
    """Start the ``pool=core`` Hatchet worker."""
    settings = get_settings()
    client = hatchet()
    workflow = build_pipeline_workflow(client)
    worker = client.worker(
        "repody-core-worker",
        slots=settings.worker_concurrency,
        durable_slots=settings.worker_concurrency,
        labels={"pool": "core"},
        workflows=[workflow],
    )
    worker.start()


if __name__ == "__main__":
    main()
