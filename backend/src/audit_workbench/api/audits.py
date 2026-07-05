from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.schemas.audit import AuditListResponse
from audit_workbench.schemas.run import RunAuditDetail
from audit_workbench.services.audit import get_audit_detail, list_completed_audits

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("", response_model=AuditListResponse)
async def list_audits(session: AsyncSession = Depends(get_session)):
    audits = await list_completed_audits(session)
    return AuditListResponse(audits=audits)


@router.get("/{audit_id}", response_model=RunAuditDetail)
async def get_audit(audit_id: str, session: AsyncSession = Depends(get_session)):
    detail = await get_audit_detail(session, audit_id)
    if not detail:
        raise HTTPException(404, "Audit not found")
    return detail
