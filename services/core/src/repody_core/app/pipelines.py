"""Multi-module durable pipeline use cases and stage orchestration."""

from collections.abc import Awaitable, Callable
from typing import Any

from repody_common.contracts import (
    ArtifactRef,
    CaseRef,
    FraudPostVerifyInput,
    FraudPreCheckInput,
    IdpStageInput,
)
from repody_common.entitlements import ModuleId
from repody_common.ids import new_id
from repody_common.ports import EntitlementProvider
from repody_core.app.ports import CoreStore, PipelineDispatcher, StageInvoker
from repody_core.schemas.errors import ForbiddenError, NotFoundError
from repody_core.schemas.pipelines import (
    FourEyesGateStage,
    FraudPostVerifyStage,
    FraudPreCheckStage,
    IdpPipelineStage,
    PipelineRunResponse,
    PipelineTaskInput,
    StartPipelineRequest,
)

STAGE_REQUIRED_MODULE: dict[str, ModuleId] = {
    "idp": "idp",
    "fraud_pre_check": "fraud",
    "fraud_post_verify": "fraud",
}


async def start_pipeline(
    store: CoreStore,
    dispatcher: PipelineDispatcher,
    entitlements: EntitlementProvider,
    *,
    case_id: str,
    actor_sub: str,
    account_id: str | None,
    request: StartPipelineRequest,
) -> PipelineRunResponse:
    """Validate entitlements, persist a pipeline run, and enqueue it on Hatchet."""
    case = await store.get_case(case_id, account=account_id)
    if case is None:
        raise NotFoundError(f"Case {case_id} was not found.")

    state = entitlements.current()
    for stage in request.stages:
        required = STAGE_REQUIRED_MODULE.get(stage.kind)
        if required is not None and not state.has_module(required):
            raise ForbiddenError(f"Module '{required}' is not licensed for this installation.")

    run = await store.create_pipeline_run(
        pipeline_id=new_id("pipe"),
        case_id=case.id,
        stages=[stage.model_dump(mode="json") for stage in request.stages],
        actor_sub=actor_sub,
        account_id=case.account_id,
    )

    case_ref = CaseRef(
        case_id=case.id,
        account_id=case.account_id,
        external_ref=case.external_ref,
        input_payload=case.input_payload,
        artifacts=[
            ArtifactRef(
                artifact_id=a.id,
                module=a.module,
                kind=a.kind,
                storage_key=a.storage_key,
                sha256=a.sha256,
                mime_type=a.mime_type,
                byte_size=a.byte_size,
            )
            for a in case.artifacts
        ],
    )
    task_input = PipelineTaskInput(
        pipeline_run_id=run.id,
        case=case_ref,
        stages=request.stages,
    )
    hatchet_run_id = await dispatcher.dispatch_pipeline(task_input)
    if hatchet_run_id:
        run = await store.set_pipeline_hatchet_run(
            pipeline_id=run.id,
            hatchet_run_id=hatchet_run_id,
        )
    return run


async def get_pipeline(
    store: CoreStore,
    *,
    pipeline_id: str,
    account_id: str | None,
) -> PipelineRunResponse:
    """Fetch a pipeline run scoped to ``account_id`` (or raise 404)."""
    run = await store.get_pipeline_run(pipeline_id, account=account_id)
    if run is None:
        raise NotFoundError(f"Pipeline {pipeline_id} was not found.")
    return run


async def execute_pipeline_stages(
    task_input: PipelineTaskInput,
    *,
    invoker: StageInvoker,
    wait_for_approval: Callable[[str], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    """Execute ordered cross-module pipeline stages using child tasks and HITL waits."""
    if not task_input.stages:
        if not task_input.approval_id:
            return {
                "case_id": task_input.case.case_id,
                "pipeline_run_id": task_input.pipeline_run_id,
                "status": "completed",
                "results": [],
            }
        wait_result = await wait_for_approval(task_input.approval_id)
        return {
            "case_id": task_input.case.case_id,
            "pipeline_run_id": task_input.pipeline_run_id,
            "approval_id": task_input.approval_id,
            "wait_result": wait_result,
        }

    results: list[dict[str, Any]] = []
    extracted_data: dict[str, Any] = {}
    pre_check_analysis_id: str | None = None
    artifacts = list(task_input.case.artifacts)

    for stage in task_input.stages:
        if isinstance(stage, FraudPreCheckStage):
            pre = await invoker.run_fraud_pre_check(
                FraudPreCheckInput(case=task_input.case, artifacts=artifacts)
            )
            pre_check_analysis_id = pre.analysis_id
            artifacts.extend(pre.generated_artifacts)
            results.append({"stage": "fraud_pre_check", "output": pre.model_dump(mode="json")})
            if stage.short_circuit_on_critical and pre.short_circuit_recommended:
                return {
                    "case_id": task_input.case.case_id,
                    "pipeline_run_id": task_input.pipeline_run_id,
                    "status": "short_circuited",
                    "results": results,
                }
        elif isinstance(stage, IdpPipelineStage):
            idp_out = await invoker.run_idp(
                IdpStageInput(
                    case=task_input.case,
                    workflow_id=stage.workflow_id,
                    artifacts=artifacts,
                )
            )
            extracted_data = dict(idp_out.extracted_data)
            results.append({"stage": "idp", "output": idp_out.model_dump(mode="json")})
        elif isinstance(stage, FraudPostVerifyStage):
            post = await invoker.run_fraud_post_verify(
                FraudPostVerifyInput(
                    case=task_input.case,
                    artifacts=artifacts,
                    extracted_data=extracted_data,
                    pre_check_analysis_id=pre_check_analysis_id,
                )
            )
            artifacts.extend(post.generated_artifacts)
            results.append({"stage": "fraud_post_verify", "output": post.model_dump(mode="json")})
        elif isinstance(stage, FourEyesGateStage):
            approval_id = stage.approval_id or task_input.approval_id
            if approval_id:
                wait_result = await wait_for_approval(approval_id)
                results.append(
                    {
                        "stage": "four_eyes_gate",
                        "approval_id": approval_id,
                        "wait_result": wait_result,
                    }
                )

    return {
        "case_id": task_input.case.case_id,
        "pipeline_run_id": task_input.pipeline_run_id,
        "status": "completed",
        "results": results,
    }
