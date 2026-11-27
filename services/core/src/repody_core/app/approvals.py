"""Four-Eyes (Maker-Checker) approval use cases and audit verification."""

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from repody_common.contracts import FourEyesApprovalEvent
from repody_common.ids import new_id
from repody_core.app.lifecycle import assert_approval_transition
from repody_core.app.ports import CoreStore, EventPublisher
from repody_core.schemas.approvals import (
    ApprovalTaskResponse,
    CheckerDecisionRequest,
    CreateApprovalRequest,
    MakerSubmitRequest,
)
from repody_core.schemas.audit import AuditChainVerificationResponse, AuditEventResponse
from repody_core.schemas.errors import ConflictError, FourEyesViolationError, NotFoundError
from repody_core.schemas.hashing import AuditChainItem, canonical_sha256, verify_audit_chain


def apply_field_override(
    snapshot: dict[str, Any],
    field_path: str,
    after_value: Any,
) -> tuple[dict[str, Any], Any]:
    """Return a copy of ``snapshot`` with ``field_path`` updated and its previous value."""
    updated = deepcopy(snapshot)
    parts = [part for part in field_path.split(".") if part]
    if not parts:
        raise ConflictError("Override field_path must not be empty.")

    cursor: dict[str, Any] = updated
    for segment in parts[:-1]:
        child = cursor.get(segment)
        if not isinstance(child, dict):
            child = {}
            cursor[segment] = child
        cursor = child

    leaf = parts[-1]
    before_value = deepcopy(cursor.get(leaf))
    cursor[leaf] = after_value
    return updated, before_value


async def create_approval(
    store: CoreStore,
    *,
    actor_sub: str,
    account_id: str | None,
    request: CreateApprovalRequest,
) -> ApprovalTaskResponse:
    """Open a Four-Eyes approval checkpoint for an existing case."""
    case = await store.get_case(request.case_id, account=account_id)
    if case is None:
        raise NotFoundError(f"Case {request.case_id} was not found.")

    payload_sha256 = canonical_sha256(request.payload_snapshot)
    return await store.create_approval(
        approval_id=new_id("apr"),
        case_id=case.id,
        stage_name=request.stage_name,
        payload_snapshot=request.payload_snapshot,
        payload_sha256=payload_sha256,
        actor_sub=actor_sub,
        account_id=case.account_id,
    )


async def get_approval(
    store: CoreStore,
    *,
    approval_id: str,
    account_id: str | None,
) -> ApprovalTaskResponse:
    """Fetch an approval task scoped to the caller's account."""
    task = await store.get_approval(approval_id)
    if task is None:
        raise NotFoundError(f"Approval {approval_id} was not found.")
    case = await store.get_case(task.case_id, account=account_id)
    if case is None:
        raise NotFoundError(f"Approval {approval_id} was not found.")
    return task


async def submit_maker_review(
    store: CoreStore,
    *,
    approval_id: str,
    maker_sub: str,
    account_id: str | None,
    request: MakerSubmitRequest,
) -> ApprovalTaskResponse:
    """Apply optional audited overrides as Maker and advance to ``waiting_checker``."""
    task = await get_approval(store, approval_id=approval_id, account_id=account_id)
    try:
        assert_approval_transition(task.status, "waiting_checker")
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc

    snapshot = deepcopy(task.payload_snapshot)
    recorded_overrides = []
    for item in request.overrides:
        snapshot, before_value = apply_field_override(snapshot, item.field_path, item.after_value)
        recorded_overrides.append((item, before_value))

    case = await store.get_case(task.case_id, account=account_id)
    return await store.apply_maker_review(
        approval_id=task.id,
        maker_sub=maker_sub,
        next_status="waiting_checker",
        case_status="waiting_checker",
        updated_snapshot=snapshot,
        payload_sha256=canonical_sha256(snapshot),
        overrides=recorded_overrides,
        note=request.note,
        account_id=case.account_id if case else None,
    )


async def submit_checker_decision(
    store: CoreStore,
    publisher: EventPublisher,
    *,
    approval_id: str,
    checker_sub: str,
    account_id: str | None,
    request: CheckerDecisionRequest,
) -> ApprovalTaskResponse:
    """Record the Checker's independent decision and resume Hatchet if waiting."""
    task = await get_approval(store, approval_id=approval_id, account_id=account_id)
    if task.status != "waiting_checker" or task.maker_sub is None:
        raise ConflictError("Approval is not ready for Checker review.")
    if checker_sub == task.maker_sub:
        raise FourEyesViolationError()

    try:
        assert_approval_transition(task.status, request.decision)
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc

    case_status = {
        "approved": "approved",
        "rejected": "rejected",
        "returned_to_maker": "waiting_maker",
    }[request.decision]

    case = await store.get_case(task.case_id, account=account_id)
    updated = await store.apply_checker_decision(
        approval_id=task.id,
        checker_sub=checker_sub,
        decision=request.decision,
        next_status=request.decision,
        case_status=case_status,  # type: ignore[arg-type]
        note=request.note,
        account_id=case.account_id if case else None,
    )

    event = FourEyesApprovalEvent(
        approval_id=updated.id,
        case_id=updated.case_id,
        payload_sha256=updated.payload_sha256,
        maker_sub=task.maker_sub,
        checker_sub=checker_sub,
        decision=request.decision,
        note=request.note,
        decided_at=updated.checker_decided_at or datetime.now(UTC),
    )
    await publisher.publish_approval_decision(event)
    return updated


async def list_audit_events(
    store: CoreStore,
    *,
    account_id: str | None,
    limit: int = 200,
) -> list[AuditEventResponse]:
    """Return ordered audit events visible to ``account_id``."""
    return await store.list_audit_events(account_id=account_id, limit=limit)


async def verify_stored_audit_chain(store: CoreStore) -> AuditChainVerificationResponse:
    """Verify the entire SHA-256 hash chain stored in ``audit_events``."""
    events = await store.list_audit_events(account_id=None, limit=10_000)
    items = [
        AuditChainItem(
            id=event.id,
            actor_sub=event.actor_sub,
            account_id=event.account_id,
            module=event.module,
            action=event.action,
            resource_id=event.resource_id,
            detail=event.detail,
            created_at_iso=event.created_at.isoformat(),
            prev_hash=event.prev_hash,
            event_hash=event.event_hash,
        )
        for event in events
    ]
    valid, checked, broken_id = verify_audit_chain(items)
    return AuditChainVerificationResponse(
        valid=valid,
        checked_count=checked,
        first_broken_id=broken_id,
    )
