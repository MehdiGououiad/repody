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
from pydantic import BaseModel, Field

from repody_common.contracts import CaseRef
from repody_core.infra.queue import APPROVAL_DECIDED_EVENT, PIPELINE_WORKFLOW, hatchet
from repody_core.settings import get_settings


class PipelineTaskInput(BaseModel):
    """Input payload for the durable cross-module pipeline orchestrator."""

    case: CaseRef
    stages: list[dict[str, Any]] = Field(default_factory=list)
    approval_id: str | None = None


def build_pipeline_workflow(client: Hatchet) -> Standalone[PipelineTaskInput, dict[str, Any]]:
    """Register the durable pipeline workflow with zero-slot HITL event waits."""
    settings = get_settings()

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
        if not input.approval_id:
            return {
                "case_id": input.case.case_id,
                "status": "completed",
                "stages": len(input.stages),
            }

        consider_since = await ctx.aio_now() - timedelta(minutes=5)
        wait_result = await ctx.aio_wait_for(
            "four-eyes-approval",
            or_(
                SleepCondition(timedelta(hours=settings.approval_sla_hours)),
                UserEventCondition(
                    event_key=APPROVAL_DECIDED_EVENT,
                    scope=input.approval_id,
                    consider_events_since=consider_since,
                ),
            ),
        )
        return {
            "case_id": input.case.case_id,
            "approval_id": input.approval_id,
            "wait_result": wait_result,
        }

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
