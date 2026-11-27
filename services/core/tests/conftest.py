"""Shared in-memory test doubles and pytest fixtures for ``repody-core`` tests."""

from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from repody_common.contracts import FourEyesApprovalEvent, FourEyesDecision
from repody_common.entitlements import (
    EntitlementState,
    LicenseClaims,
    ModuleId,
    sign_license_token,
    verify_license_token,
)
from repody_common.ids import new_id
from repody_core.schemas.approvals import (
    ApprovalStatus,
    ApprovalTaskResponse,
    FieldOverrideInput,
    FieldOverrideResponse,
)
from repody_core.schemas.audit import AuditEventResponse
from repody_core.schemas.cases import CaseResponse, CaseStatus, CreateCaseRequest
from repody_core.schemas.hashing import GENESIS_HASH, compute_event_hash
from repody_core.schemas.pipelines import PipelineRunResponse, PipelineTaskInput


class InMemoryCoreStore:
    """In-memory ``CoreStore`` for fast, isolated FastAPI contract tests."""

    def __init__(self) -> None:
        self.cases: dict[str, CaseResponse] = {}
        self.pipelines: dict[str, PipelineRunResponse] = {}
        self.approvals: dict[str, ApprovalTaskResponse] = {}
        self.events: list[AuditEventResponse] = []

    def _append(
        self,
        *,
        actor_sub: str,
        account_id: str | None,
        module: str,
        action: str,
        resource_id: str,
        detail: dict[str, Any],
    ) -> None:
        prev_hash = self.events[-1].event_hash if self.events else GENESIS_HASH
        event_id = new_id("evt")
        now = datetime.now(UTC)
        event_hash = compute_event_hash(
            prev_hash,
            event_id=event_id,
            actor_sub=actor_sub,
            account_id=account_id,
            module=module,
            action=action,
            resource_id=resource_id,
            detail=detail,
            created_at_iso=now.isoformat(),
        )
        self.events.append(
            AuditEventResponse(
                seq=len(self.events) + 1,
                id=event_id,
                actor_sub=actor_sub,
                account_id=account_id,
                module=module,
                action=action,
                resource_id=resource_id,
                detail=detail,
                prev_hash=prev_hash,
                event_hash=event_hash,
                created_at=now,
            )
        )

    async def create_case(
        self,
        *,
        case_id: str,
        actor_sub: str,
        request: CreateCaseRequest,
    ) -> CaseResponse:
        now = datetime.now(UTC)
        case = CaseResponse(
            id=case_id,
            account_id=request.account_id,
            external_ref=request.external_ref,
            input_payload=deepcopy(request.input_payload),
            status="open",
            created_by=actor_sub,
            created_at=now,
            updated_at=now,
            artifacts=[],
        )
        self.cases[case_id] = case
        self._append(
            actor_sub=actor_sub,
            account_id=request.account_id,
            module="core",
            action="case.created",
            resource_id=case_id,
            detail={"artifact_count": len(request.artifacts)},
        )
        return case

    async def get_case(self, case_id: str, *, account: str | None) -> CaseResponse | None:
        case = self.cases.get(case_id)
        if case is None or (account is not None and case.account_id != account):
            return None
        return case

    async def create_pipeline_run(
        self,
        *,
        pipeline_id: str,
        case_id: str,
        stages: list[dict[str, Any]],
        actor_sub: str,
        account_id: str | None,
    ) -> PipelineRunResponse:
        now = datetime.now(UTC)
        run = PipelineRunResponse(
            id=pipeline_id,
            case_id=case_id,
            stages=deepcopy(stages),
            status="queued",
            hatchet_run_id=None,
            created_at=now,
            finished_at=None,
        )
        self.pipelines[pipeline_id] = run
        self._append(
            actor_sub=actor_sub,
            account_id=account_id,
            module="core",
            action="pipeline.started",
            resource_id=pipeline_id,
            detail={"case_id": case_id, "stage_count": len(stages)},
        )
        return run

    async def set_pipeline_hatchet_run(
        self,
        *,
        pipeline_id: str,
        hatchet_run_id: str,
    ) -> PipelineRunResponse:
        updated = self.pipelines[pipeline_id].model_copy(update={"hatchet_run_id": hatchet_run_id})
        self.pipelines[pipeline_id] = updated
        return updated

    async def get_pipeline_run(
        self,
        pipeline_id: str,
        *,
        account: str | None,
    ) -> PipelineRunResponse | None:
        run = self.pipelines.get(pipeline_id)
        if run is None:
            return None
        case = self.cases.get(run.case_id)
        if account is not None and (case is None or case.account_id != account):
            return None
        return run

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
    ) -> ApprovalTaskResponse:
        now = datetime.now(UTC)
        task = ApprovalTaskResponse(
            id=approval_id,
            case_id=case_id,
            stage_name=stage_name,
            status="waiting_maker",
            payload_snapshot=deepcopy(payload_snapshot),
            payload_sha256=payload_sha256,
            maker_sub=None,
            maker_note="",
            maker_decided_at=None,
            checker_sub=None,
            checker_note="",
            checker_decided_at=None,
            created_at=now,
            updated_at=now,
            overrides=[],
        )
        self.approvals[approval_id] = task
        self._append(
            actor_sub=actor_sub,
            account_id=account_id,
            module="core",
            action="approval.created",
            resource_id=approval_id,
            detail={"case_id": case_id, "payload_sha256": payload_sha256},
        )
        return task

    async def get_approval(self, approval_id: str) -> ApprovalTaskResponse | None:
        return self.approvals.get(approval_id)

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
    ) -> ApprovalTaskResponse:
        now = datetime.now(UTC)
        existing = self.approvals[approval_id]
        new_overrides = [
            FieldOverrideResponse(
                id=new_id("ov"),
                case_id=existing.case_id,
                approval_task_id=approval_id,
                field_path=item.field_path,
                before_value=before_val,
                after_value=item.after_value,
                actor_sub=maker_sub,
                reason=item.reason,
                created_at=now,
            )
            for item, before_val in overrides
        ]
        updated = existing.model_copy(
            update={
                "status": next_status,
                "payload_snapshot": deepcopy(updated_snapshot),
                "payload_sha256": payload_sha256,
                "maker_sub": maker_sub,
                "maker_note": note,
                "maker_decided_at": now,
                "updated_at": now,
                "overrides": [*existing.overrides, *new_overrides],
            }
        )
        self.approvals[approval_id] = updated
        case = self.cases[existing.case_id]
        self.cases[existing.case_id] = case.model_copy(
            update={"status": case_status, "updated_at": now}
        )
        self._append(
            actor_sub=maker_sub,
            account_id=account_id,
            module="core",
            action="approval.maker_submitted",
            resource_id=approval_id,
            detail={
                "case_id": existing.case_id,
                "override_count": len(overrides),
                "payload_sha256": payload_sha256,
            },
        )
        return updated

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
    ) -> ApprovalTaskResponse:
        now = datetime.now(UTC)
        existing = self.approvals[approval_id]
        updated = existing.model_copy(
            update={
                "status": next_status,
                "checker_sub": checker_sub,
                "checker_note": note,
                "checker_decided_at": now,
                "updated_at": now,
            }
        )
        self.approvals[approval_id] = updated
        case = self.cases[existing.case_id]
        self.cases[existing.case_id] = case.model_copy(
            update={"status": case_status, "updated_at": now}
        )
        self._append(
            actor_sub=checker_sub,
            account_id=account_id,
            module="core",
            action="approval.checker_decided",
            resource_id=approval_id,
            detail={
                "case_id": existing.case_id,
                "decision": decision,
                "payload_sha256": existing.payload_sha256,
            },
        )
        return updated

    async def list_audit_events(
        self,
        *,
        account_id: str | None = None,
        limit: int = 200,
    ) -> list[AuditEventResponse]:
        items = [e for e in self.events if account_id is None or e.account_id == account_id]
        return items[:limit]


class FakeHatchetGateway:
    """Captures emitted approval events and dispatched pipelines."""

    def __init__(self) -> None:
        self.events: list[FourEyesApprovalEvent] = []
        self.dispatched: list[PipelineTaskInput] = []

    async def publish_approval_decision(self, event: FourEyesApprovalEvent) -> None:
        self.events.append(event)

    async def dispatch_pipeline(self, task_input: PipelineTaskInput) -> str | None:
        self.dispatched.append(task_input)
        return f"hatchet-{len(self.dispatched)}"


class StaticEntitlementProvider:
    """Offline Ed25519 entitlement provider backed by a test keypair."""

    def __init__(self, modules: tuple[ModuleId, ...] = ("idp", "fraud")) -> None:
        key = Ed25519PrivateKey.generate()
        private_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode()
        self.public_pem = (
            key.public_key()
            .public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            .decode()
        )
        now = datetime.now(UTC)
        self.token = sign_license_token(
            LicenseClaims(
                customer_id="bank-atlas",
                modules=modules,
                issued_at=now - timedelta(hours=1),
                expires_at=now + timedelta(days=90),
            ),
            private_pem,
        )

    def current(self) -> EntitlementState:
        return verify_license_token(self.token, self.public_pem)


@pytest.fixture
def core_store() -> InMemoryCoreStore:
    return InMemoryCoreStore()


@pytest.fixture
def core_gateway() -> FakeHatchetGateway:
    return FakeHatchetGateway()


@pytest.fixture
def entitlement_factory() -> Callable[[tuple[ModuleId, ...]], StaticEntitlementProvider]:
    def _build(modules: tuple[ModuleId, ...] = ("idp", "fraud")) -> StaticEntitlementProvider:
        return StaticEntitlementProvider(modules=modules)

    return _build
