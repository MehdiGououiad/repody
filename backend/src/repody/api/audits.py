from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from repody.api.auth import require_permission
from repody.api.deps import SessionDep
from repody.app.audit.query import list_audit_page
from repody.app.run.intake import get_run_detail
from repody.schemas.audit import AuditListResponse
from repody.schemas.run import RunAuditDetail

router = APIRouter(
    prefix="/audits",
    tags=["audits"],
    dependencies=[Depends(require_permission("audit", "read"))],
)


@router.get("", response_model=AuditListResponse)
async def list_audits(
    session: SessionDep,
    limit: int = 50,
    offset: int = 0,
):
    return await list_audit_page(session, limit=limit, offset=offset)


@router.get("/{audit_id}", response_model=RunAuditDetail)
async def get_audit(audit_id: str, session: SessionDep):
    detail = await get_run_detail(session, audit_id)
    if not detail:
        raise HTTPException(404, "Audit not found")
    return detail
