"""Protocol ports for persistence and durable event publishing."""

from typing import Any, Protocol

from repody_common.contracts import FourEyesApprovalEvent, FourEyesDecision
from repody_core.schemas.approvals import (
    ApprovalStatus,
    ApprovalTaskResponse,
    FieldOverrideInput,
)
from repody_core.schemas.audit import AuditEventResponse
from repody_core.schemas.cases import CaseResponse, CaseStatus, CreateCaseRequest


class CoreStore(Protocol):
    """Persistence port for ``repody_core`` cases, approvals, and audit chain."""

    async def create_case(
        self,
        *,
        case_id: str,
        actor_sub: str,
        request: CreateCaseRequest,
    ) -> CaseResponse: ...

    async def get_case(self, case_id: str, *, account: str | None) -> CaseResponse | None: ...

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
