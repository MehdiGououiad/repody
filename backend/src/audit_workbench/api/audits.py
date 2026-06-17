from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.api.deps import get_session
from audit_workbench.db.models import Run, RunStatus
from audit_workbench.schemas.audit import AuditListResponse
from audit_workbench.schemas.run import RunAuditDetail
from audit_workbench.services.mappers import run_to_audit_list_item

router = APIRouter(prefix="/audits", tags=["audits"])


@router.get("", response_model=AuditListResponse)
async def list_audits(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Run)
        .where(Run.status == RunStatus.done.value)
        .order_by(Run.created_at.desc())
        .limit(100)
        .options(selectinload(Run.workflow))
    )
    runs = result.scalars().all()
    audits = [
        run_to_audit_list_item(r, r.workflow.name if r.workflow else "Workflow") for r in runs
    ]
    return AuditListResponse(audits=audits)


@router.get("/{audit_id}", response_model=RunAuditDetail)
async def get_audit(audit_id: str, session: AsyncSession = Depends(get_session)):
    from audit_workbench.services.run_service import get_run_detail

    detail = await get_run_detail(session, audit_id)
    if not detail:
        raise HTTPException(404, "Audit not found")
    return detail
