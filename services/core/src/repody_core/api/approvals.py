"""Four-Eyes (Maker-Checker) approval endpoints."""

from typing import Annotated

from fastapi import APIRouter

from repody_core.api.deps import PublisherDep, StoreDep, require
from repody_core.app import approvals as app_approvals
from repody_core.infra.auth import CoreUser
from repody_core.schemas.approvals import (
    ApprovalTaskResponse,
    CheckerDecisionRequest,
    CreateApprovalRequest,
    MakerSubmitRequest,
)

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.post("", status_code=201)
async def create_approval(
    body: CreateApprovalRequest,
    store: StoreDep,
    user: Annotated[CoreUser, require("approval:make")],
) -> ApprovalTaskResponse:
    """Open a Four-Eyes approval checkpoint for a case."""
    return await app_approvals.create_approval(
        store,
        actor_sub=user.subject,
        account_id=user.account,
        request=body,
    )


@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    store: StoreDep,
    user: Annotated[CoreUser, require("approval:read")],
) -> ApprovalTaskResponse:
    """Read a Four-Eyes approval task and its audited field overrides."""
    return await app_approvals.get_approval(
        store,
        approval_id=approval_id,
        account_id=user.account,
    )


@router.post("/{approval_id}/make")
async def submit_maker_review(
    approval_id: str,
    body: MakerSubmitRequest,
    store: StoreDep,
    user: Annotated[CoreUser, require("approval:make")],
) -> ApprovalTaskResponse:
    """Record Maker review and optional field overrides, advancing to Checker."""
    return await app_approvals.submit_maker_review(
        store,
        approval_id=approval_id,
        maker_sub=user.subject,
        account_id=user.account,
        request=body,
    )


@router.post("/{approval_id}/check")
async def submit_checker_decision(
    approval_id: str,
    body: CheckerDecisionRequest,
    store: StoreDep,
    publisher: PublisherDep,
    user: Annotated[CoreUser, require("approval:check")],
) -> ApprovalTaskResponse:
    """Record independent Checker decision and notify Hatchet."""
    return await app_approvals.submit_checker_decision(
        store,
        publisher,
        approval_id=approval_id,
        checker_sub=user.subject,
        account_id=user.account,
        request=body,
    )
