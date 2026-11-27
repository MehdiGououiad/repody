"""Hatchet workers for Fraud Shield CPU (``fraud-cpu``) and GPU (``fraud-gpu``) pools."""

from datetime import timedelta
from typing import Any

from hatchet_sdk import Context, DesiredWorkerLabel, Hatchet
from hatchet_sdk.runnables.workflow import BaseWorkflow, Standalone

from repody_common.contracts import (
    FraudPostVerifyInput,
    FraudPostVerifyOutput,
    FraudPreCheckInput,
    FraudPreCheckOutput,
)
from repody_fraud.app.service import FraudService
from repody_fraud.infra import db
from repody_fraud.infra.explainer import build_explainer
from repody_fraud.infra.queue import FRAUD_POST_VERIFY_TASK, FRAUD_PRE_CHECK_TASK, hatchet
from repody_fraud.infra.repository import SqlFraudStore
from repody_fraud.infra.storage import get_s3_storage
from repody_fraud.settings import get_settings


def build_pre_check_workflow(
    client: Hatchet,
) -> Standalone[FraudPreCheckInput, FraudPreCheckOutput]:
    """Register ``fraud.pre_check`` pinned to CPU workers (``pool=fraud-cpu``)."""

    @client.task(
        name=FRAUD_PRE_CHECK_TASK,
        input_validator=FraudPreCheckInput,
        execution_timeout=timedelta(minutes=5),
        retries=2,
        desired_worker_labels=[DesiredWorkerLabel(key="pool", value="fraud-cpu", required=True)],
    )
    async def pre_check(input: FraudPreCheckInput, _ctx: Context) -> FraudPreCheckOutput:
        async with db.get_session_factory()() as session:
            service = FraudService(
                store=SqlFraudStore(session),
                storage=get_s3_storage(),
                explainer=build_explainer(),
            )
            return await service.run_pre_check(input)

    return pre_check


def build_post_verify_workflow(
    client: Hatchet,
) -> Standalone[FraudPostVerifyInput, FraudPostVerifyOutput]:
    """Register ``fraud.post_verify`` pinned to GPU/visual workers (``pool=fraud-gpu``)."""

    @client.task(
        name=FRAUD_POST_VERIFY_TASK,
        input_validator=FraudPostVerifyInput,
        execution_timeout=timedelta(minutes=10),
        retries=2,
        desired_worker_labels=[DesiredWorkerLabel(key="pool", value="fraud-gpu", required=True)],
    )
    async def post_verify(input: FraudPostVerifyInput, _ctx: Context) -> FraudPostVerifyOutput:
        async with db.get_session_factory()() as session:
            service = FraudService(
                store=SqlFraudStore(session),
                storage=get_s3_storage(),
                explainer=build_explainer(),
            )
            return await service.run_post_verify(input)

    return post_verify


def main() -> None:
    """Start the configured Fraud Shield Hatchet worker pool."""
    settings = get_settings()
    client = hatchet()
    pool = settings.worker_pool.strip().lower()

    if pool == "fraud-cpu":
        workflows: list[BaseWorkflow[Any]] = [build_pre_check_workflow(client)]
        labels: dict[str, str | int] = {"pool": "fraud-cpu"}
        name = "repody-fraud-cpu-worker"
    elif pool == "fraud-gpu":
        workflows = [build_post_verify_workflow(client)]
        labels = {"pool": "fraud-gpu"}
        name = "repody-fraud-gpu-worker"
    else:
        workflows = [build_pre_check_workflow(client), build_post_verify_workflow(client)]
        labels = {"pool": "fraud-cpu"}
        name = "repody-fraud-worker"

    worker = client.worker(
        name,
        slots=settings.worker_concurrency,
        labels=labels,
        workflows=workflows,
    )
    worker.start()


if __name__ == "__main__":
    main()
