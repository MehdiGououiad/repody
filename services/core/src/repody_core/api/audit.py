"""Regulatory audit log query and cryptographic chain verification endpoints."""

from typing import Annotated

from fastapi import APIRouter, Query

from repody_core.api.deps import StoreDep, require
from repody_core.app import approvals as app_approvals
from repody_core.infra.auth import CoreUser
from repody_core.schemas.audit import AuditChainVerificationResponse, AuditEventResponse

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("")
async def list_audit_events(
    store: StoreDep,
    user: Annotated[CoreUser, require("audit:read")],
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[AuditEventResponse]:
    """List hash-chained regulatory audit events visible to the caller."""
    return await app_approvals.list_audit_events(store, account_id=user.account, limit=limit)


@router.get("/verify")
async def verify_audit_chain(
    store: StoreDep,
    _user: Annotated[CoreUser, require("audit:verify")],
) -> AuditChainVerificationResponse:
    """Verify SHA-256 hash-chain integrity across all stored audit events."""
    return await app_approvals.verify_stored_audit_chain(store)
