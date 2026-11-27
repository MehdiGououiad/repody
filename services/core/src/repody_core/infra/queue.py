"""Hatchet durable event publisher, pipeline dispatcher, and child-task stub invoker."""

from functools import cache

import structlog
from hatchet_sdk import DesiredWorkerLabel, Hatchet

from repody_common.contracts import (
    FourEyesApprovalEvent,
    FraudPostVerifyInput,
    FraudPostVerifyOutput,
    FraudPreCheckInput,
    FraudPreCheckOutput,
    IdpStageInput,
    IdpStageOutput,
)
from repody_core.schemas.pipelines import PipelineTaskInput
from repody_core.settings import get_settings

log = structlog.get_logger(__name__)

PIPELINE_WORKFLOW = "pipeline-execute"
APPROVAL_DECIDED_EVENT = "approval:decided"
IDP_STAGE_TASK = "idp.extract_and_validate"
FRAUD_PRE_CHECK_TASK = "fraud.pre_check"
FRAUD_POST_VERIFY_TASK = "fraud.post_verify"


@cache
def hatchet() -> Hatchet:
    """Return the cached Hatchet client (reads ``HATCHET_CLIENT_*`` on first use)."""
    return Hatchet()


class HatchetEventPublisher:
    """Publish Four-Eyes decisions and dispatch durable multi-module pipelines."""

    async def publish_approval_decision(self, event: FourEyesApprovalEvent) -> None:
        if not get_settings().hatchet_enabled:
            return
        await hatchet().event.aio_push(
            event_key=APPROVAL_DECIDED_EVENT,
            payload=event.model_dump(mode="json"),
            scope=event.approval_id,
        )
        log.info(
            "hatchet_approval_event_pushed",
            approval_id=event.approval_id,
            decision=event.decision,
        )

    async def dispatch_pipeline(self, task_input: PipelineTaskInput) -> str | None:
        if not get_settings().hatchet_enabled:
            return None
        stub = hatchet().stubs.task(
            name=PIPELINE_WORKFLOW,
            input_validator=PipelineTaskInput,
        )
        ref = await stub.aio_run_no_wait(
            task_input,
            desired_worker_labels=[DesiredWorkerLabel(key="pool", value="core", required=True)],
        )
        log.info(
            "hatchet_pipeline_dispatched",
            pipeline_run_id=task_input.pipeline_run_id,
            hatchet_run_id=ref.workflow_run_id,
        )
        return ref.workflow_run_id


class HatchetStageInvoker:
    """Invoke remote IDP and Fraud Shield Hatchet tasks via official type-safe stubs."""

    def __init__(self, client: Hatchet) -> None:
        self._idp_stub = client.stubs.task(
            name=IDP_STAGE_TASK,
            input_validator=IdpStageInput,
            output_validator=IdpStageOutput,
        )
        self._fraud_pre_stub = client.stubs.task(
            name=FRAUD_PRE_CHECK_TASK,
            input_validator=FraudPreCheckInput,
            output_validator=FraudPreCheckOutput,
        )
        self._fraud_post_stub = client.stubs.task(
            name=FRAUD_POST_VERIFY_TASK,
            input_validator=FraudPostVerifyInput,
            output_validator=FraudPostVerifyOutput,
        )

    async def run_idp(self, payload: IdpStageInput) -> IdpStageOutput:
        return await self._idp_stub.aio_run(
            payload,
            wait_for_result=True,
            desired_worker_labels=[DesiredWorkerLabel(key="pool", value="idp", required=True)],
        )

    async def run_fraud_pre_check(self, payload: FraudPreCheckInput) -> FraudPreCheckOutput:
        return await self._fraud_pre_stub.aio_run(
            payload,
            wait_for_result=True,
            desired_worker_labels=[
                DesiredWorkerLabel(key="pool", value="fraud-cpu", required=True)
            ],
        )

    async def run_fraud_post_verify(self, payload: FraudPostVerifyInput) -> FraudPostVerifyOutput:
        return await self._fraud_post_stub.aio_run(
            payload,
            wait_for_result=True,
            desired_worker_labels=[
                DesiredWorkerLabel(key="pool", value="fraud-gpu", required=True)
            ],
        )
