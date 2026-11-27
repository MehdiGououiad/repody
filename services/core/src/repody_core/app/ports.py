"""Protocol ports for persistence, durable orchestration, and child stage execution."""

from typing import Any, Protocol

from repody_common.contracts import (
    FourEyesApprovalEvent,
    FourEyesDecision,
    FraudPostVerifyInput,
    FraudPostVerifyOutput,
    FraudPreCheckInput,
    FraudPreCheckOutput,
    IdpStageInput,
    IdpStageOutput,
)
from repody_core.schemas.approvals import (
    ApprovalStatus,
    ApprovalTaskResponse,
    FieldOverrideInput,
)
from repody_core.schemas.audit import AuditEventResponse
from repody_core.schemas.cases import CaseResponse, CaseStatus, CreateCaseRequest
from repody_core.schemas.pipelines import PipelineRunResponse, PipelineTaskInput


class CoreStore(Protocol):
    """Persistence port for ``repody_core`` cases, pipelines, approvals, and audit chain."""

    async def create_case(
        self,
        *,
        case_id: str,
        actor_sub: str,
        request: CreateCaseRequest,
    ) -> CaseResponse: ...

    async def get_case(self, case_id: str, *, account: str | None) -> CaseResponse | None: ...

    async def create_pipeline_run(
        self,
        *,
        pipeline_id: str,
        case_id: str,
        stages: list[dict[str, Any]],
        actor_sub: str,
        account_id: str | None,
    ) -> PipelineRunResponse: ...

    async def set_pipeline_hatchet_run(
        self,
        *,
        pipeline_id: str,
        hatchet_run_id: str,
    ) -> PipelineRunResponse: ...

    async def get_pipeline_run(
        self,
        pipeline_id: str,
        *,
        account: str | None,
    ) -> PipelineRunResponse | None: ...

    async def create_approval(
        self,
        *,
        approval_id: str,
        case_id: str,
        stage_name: str,
        payload_snapshot: dict[str, Any],
        payload_sha256: str,
        actor_sub: str,
        account_id: str | None,
    ) -> ApprovalTaskResponse: ...

    async def get_approval(self, approval_id: str) -> ApprovalTaskResponse | None: ...

    async def apply_maker_review(
        self,
        *,
        approval_id: str,
        maker_sub: str,
        next_status: ApprovalStatus,
        case_status: CaseStatus,
        updated_snapshot: dict[str, Any],
        payload_sha256: str,
        overrides: list[tuple[FieldOverrideInput, Any]],
        note: str,
        account_id: str | None,
    ) -> ApprovalTaskResponse: ...

    async def apply_checker_decision(
        self,
        *,
        approval_id: str,
        checker_sub: str,
        decision: FourEyesDecision,
        next_status: ApprovalStatus,
        case_status: CaseStatus,
        note: str,
        account_id: str | None,
    ) -> ApprovalTaskResponse: ...

    async def list_audit_events(
        self,
        *,
        account_id: str | None = None,
        limit: int = 200,
    ) -> list[AuditEventResponse]: ...


class EventPublisher(Protocol):
    """Port for notifying the Hatchet durable orchestrator of external decisions."""

    async def publish_approval_decision(self, event: FourEyesApprovalEvent) -> None: ...


class PipelineDispatcher(Protocol):
    """Port for queuing durable pipeline executions on ``pool=core``."""

    async def dispatch_pipeline(self, task_input: PipelineTaskInput) -> str | None: ...


class StageInvoker(Protocol):
    """Port for invoking module tasks (IDP, Fraud Shield) from Core's orchestrator."""

    async def run_idp(self, payload: IdpStageInput) -> IdpStageOutput: ...

    async def run_fraud_pre_check(self, payload: FraudPreCheckInput) -> FraudPreCheckOutput: ...

    async def run_fraud_post_verify(
        self, payload: FraudPostVerifyInput
    ) -> FraudPostVerifyOutput: ...
