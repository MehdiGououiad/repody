from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.schemas.audit import AuditListResponse
from audit_workbench.schemas.run import RunAuditDetail
from audit_workbench.services.audit import count_completed_audits, get_audit_detail, list_completed_audits

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("", response_model=AuditListResponse)
async def list_audits(
    session: AsyncSession = Depends(get_session),
    limit: int = 200,
    offset: int = 0,
):
    bounded_limit = max(1, min(limit, 500))
    bounded_offset = max(0, offset)
    total = await count_completed_audits(session)
    audits = await list_completed_audits(session, limit=bounded_limit, offset=bounded_offset)
    return AuditListResponse(
        audits=audits,
        total=total,
        limit=bounded_limit,
        offset=bounded_offset,
    )


@router.get("/{audit_id}", response_model=RunAuditDetail)
async def get_audit(audit_id: str, session: AsyncSession = Depends(get_session)):
    detail = await get_audit_detail(session, audit_id)
    if not detail:
        raise HTTPException(404, "Audit not found")
    return detail
