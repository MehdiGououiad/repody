from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.db.models import Run, RunStatus
from audit_workbench.schemas.audit import AuditListItem
from audit_workbench.services.mappers import run_to_audit_detail, run_to_audit_list_item


async def list_audits(session: AsyncSession) -> list[AuditListItem]:
    result = await session.execute(
        select(Run)
        .where(Run.status == RunStatus.done.value)
        .order_by(Run.created_at.desc())
        .limit(100)
        .options(selectinload(Run.workflow))
    )
    runs = result.scalars().all()
    return [
        run_to_audit_list_item(r, r.workflow.name if r.workflow else "Workflow")
        for r in runs
    ]


async def get_audit(session: AsyncSession, audit_id: str):
    from audit_workbench.services.run_service import get_run_detail

    return await get_run_detail(session, audit_id)
