"""SQLAlchemy 2.1 async repository implementing ``CoreStore``."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody_common.contracts import FourEyesDecision
from repody_common.ids import new_id
from repody_core.infra.models import (
    ApprovalTask,
    Artifact,
    AuditEvent,
    Case,
    FieldOverride,
)
from repody_core.schemas.approvals import (
    ApprovalStatus,
    ApprovalTaskResponse,
    FieldOverrideInput,
    FieldOverrideResponse,
)
from repody_core.schemas.audit import AuditEventResponse
from repody_core.schemas.cases import (
    ArtifactResponse,
    CaseResponse,
    CaseStatus,
    CreateCaseRequest,
)
from repody_core.schemas.errors import ConflictError, FourEyesViolationError, NotFoundError
from repody_core.schemas.hashing import GENESIS_HASH, compute_event_hash


def _case_to_schema(case: Case) -> CaseResponse:
    return CaseResponse(
        id=case.id,
        account_id=case.account_id,
        external_ref=case.external_ref,
        input_payload=case.input_payload,
        status=case.status,
        created_by=case.created_by,
        created_at=case.created_at,
        updated_at=case.updated_at,
        artifacts=[
            ArtifactResponse(
                id=a.id,
                case_id=a.case_id,
                module=a.module,
                kind=a.kind,
                storage_key=a.storage_key,
                sha256=a.sha256,
                mime_type=a.mime_type,
                byte_size=a.byte_size,
                created_at=a.created_at,
            )
            for a in case.artifacts
        ],
    )


def _approval_to_schema(
    task: ApprovalTask,
    overrides: list[FieldOverride],
) -> ApprovalTaskResponse:
    return ApprovalTaskResponse(
        id=task.id,
        case_id=task.case_id,
        stage_name=task.stage_name,
        status=task.status,
        payload_snapshot=task.payload_snapshot,
        payload_sha256=task.payload_sha256,
        maker_sub=task.maker_sub,
        maker_note=task.maker_note,
        maker_decided_at=task.maker_decided_at,
        checker_sub=task.checker_sub,
        checker_note=task.checker_note,
        checker_decided_at=task.checker_decided_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        overrides=[
            FieldOverrideResponse(
                id=ov.id,
                case_id=ov.case_id,
                approval_task_id=ov.approval_task_id,
                field_path=ov.field_path,
                before_value=ov.before_value,
                after_value=ov.after_value,
                actor_sub=ov.actor_sub,
                reason=ov.reason,
                created_at=ov.created_at,
            )
            for ov in overrides
        ],
    )


class SqlCoreStore:
    """Postgres-backed ``CoreStore`` with hash-chained audit logging."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _append_audit(
        self,
        *,
        actor_sub: str,
        account_id: str | None,
        module: str,
        action: str,
        resource_id: str,
        detail: dict[str, Any],
    ) -> AuditEvent:
        prev_hash = (
            await self._session.scalar(
                select(AuditEvent.event_hash)
                .order_by(AuditEvent.seq.desc())
                .limit(1)
                .with_for_update()
            )
        ) or GENESIS_HASH
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
        row = AuditEvent(
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
        self._session.add(row)
        return row

    async def create_case(
        self,
        *,
        case_id: str,
        actor_sub: str,
        request: CreateCaseRequest,
    ) -> CaseResponse:
        now = datetime.now(UTC)
        case = Case(
            id=case_id,
            account_id=request.account_id,
            external_ref=request.external_ref,
            input_payload=request.input_payload,
            status="open",
            created_by=actor_sub,
            created_at=now,
            updated_at=now,
            artifacts=[
                Artifact(
                    id=new_id("art"),
                    case_id=case_id,
                    module=item.module,
                    kind=item.kind,
                    storage_key=item.storage_key,
                    sha256=item.sha256,
                    mime_type=item.mime_type,
                    byte_size=item.byte_size,
                    created_at=now,
                )
                for item in request.artifacts
            ],
        )
        self._session.add(case)
        await self._append_audit(
            actor_sub=actor_sub,
            account_id=request.account_id,
            module="core",
            action="case.created",
            resource_id=case_id,
            detail={"artifact_count": len(request.artifacts)},
        )
        await self._session.commit()
        await self._session.refresh(case, attribute_names=["artifacts"])
        return _case_to_schema(case)

    async def get_case(self, case_id: str, *, account: str | None) -> CaseResponse | None:
        stmt = select(Case).options(selectinload(Case.artifacts)).where(Case.id == case_id)
        if account is not None:
            stmt = stmt.where(Case.account_id == account)
        case = await self._session.scalar(stmt)
        return _case_to_schema(case) if case else None

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
        task = ApprovalTask(
            id=approval_id,
            case_id=case_id,
            stage_name=stage_name,
            status="waiting_maker",
            payload_snapshot=payload_snapshot,
            payload_sha256=payload_sha256,
            created_at=now,
            updated_at=now,
        )
        self._session.add(task)
        await self._append_audit(
            actor_sub=actor_sub,
            account_id=account_id,
            module="core",
            action="approval.created",
            resource_id=approval_id,
            detail={"case_id": case_id, "payload_sha256": payload_sha256},
        )
        await self._session.commit()
        return _approval_to_schema(task, [])

    async def get_approval(self, approval_id: str) -> ApprovalTaskResponse | None:
        task = await self._session.get(ApprovalTask, approval_id)
        if task is None:
            return None
        overrides = list(
            await self._session.scalars(
                select(FieldOverride)
                .where(FieldOverride.approval_task_id == approval_id)
                .order_by(FieldOverride.created_at.asc())
            )
        )
        return _approval_to_schema(task, overrides)

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
        task = await self._session.scalar(
            select(ApprovalTask).where(ApprovalTask.id == approval_id).with_for_update()
        )
        if task is None:
            raise NotFoundError(f"Approval {approval_id} was not found.")
        case = await self._session.get(Case, task.case_id)
        if case is None:
            raise NotFoundError(f"Case {task.case_id} was not found.")

        now = datetime.now(UTC)
        task.status = next_status
        task.payload_snapshot = updated_snapshot
        task.payload_sha256 = payload_sha256
        task.maker_sub = maker_sub
        task.maker_note = note
        task.maker_decided_at = now
        task.updated_at = now
        case.status = case_status
        case.updated_at = now

        for item, before_val in overrides:
            self._session.add(
                FieldOverride(
                    id=new_id("ov"),
                    case_id=task.case_id,
                    approval_task_id=task.id,
                    field_path=item.field_path,
                    before_value=before_val,
                    after_value=item.after_value,
                    actor_sub=maker_sub,
                    reason=item.reason,
                    created_at=now,
                )
            )

        await self._append_audit(
            actor_sub=maker_sub,
            account_id=account_id,
            module="core",
            action="approval.maker_submitted",
            resource_id=task.id,
            detail={
                "case_id": task.case_id,
                "override_count": len(overrides),
                "payload_sha256": payload_sha256,
            },
        )
        await self._session.commit()
        return await self.get_approval(approval_id)  # type: ignore[return-value]

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
        task = await self._session.scalar(
            select(ApprovalTask).where(ApprovalTask.id == approval_id).with_for_update()
        )
        if task is None:
            raise NotFoundError(f"Approval {approval_id} was not found.")
        case = await self._session.get(Case, task.case_id)
        if case is None:
            raise NotFoundError(f"Case {task.case_id} was not found.")

        now = datetime.now(UTC)
        task.status = next_status
        task.checker_sub = checker_sub
        task.checker_note = note
        task.checker_decided_at = now
        task.updated_at = now
        case.status = case_status
        case.updated_at = now

        await self._append_audit(
            actor_sub=checker_sub,
            account_id=account_id,
            module="core",
            action="approval.checker_decided",
            resource_id=task.id,
            detail={
                "case_id": task.case_id,
                "decision": decision,
                "payload_sha256": task.payload_sha256,
            },
        )
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            if "four_eyes_distinct_actors" in str(exc):
                raise FourEyesViolationError() from exc
            raise ConflictError("Approval decision conflicted with existing state.") from exc
        return await self.get_approval(approval_id)  # type: ignore[return-value]

    async def list_audit_events(
        self,
        *,
        account_id: str | None = None,
        limit: int = 200,
    ) -> list[AuditEventResponse]:
        stmt = select(AuditEvent).order_by(AuditEvent.seq.asc()).limit(limit)
        if account_id is not None:
            stmt = stmt.where(AuditEvent.account_id == account_id)
        rows = list(await self._session.scalars(stmt))
        return [
            AuditEventResponse(
                seq=row.seq,
                id=row.id,
                actor_sub=row.actor_sub,
                account_id=row.account_id,
                module=row.module,
                action=row.action,
                resource_id=row.resource_id,
                detail=row.detail,
                prev_hash=row.prev_hash,
                event_hash=row.event_hash,
                created_at=row.created_at,
            )
            for row in rows
        ]
