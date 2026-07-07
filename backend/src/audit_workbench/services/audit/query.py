"""Audit read module — completed runs exposed as audit list/detail."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.db.models import Run, RunStatus
from audit_workbench.schemas.audit import AuditListItem
from audit_workbench.schemas.run import RunAuditDetail
from audit_workbench.services.mappers import run_to_audit_list_item
from audit_workbench.services.run_service import get_run_detail

_DEFAULT_LIST_LIMIT = 200
_MAX_LIST_LIMIT = 500


async def count_completed_audits(session: AsyncSession) -> int:
    total_q = await session.execute(
        select(func.count(Run.id)).where(Run.status == RunStatus.done.value)
    )
    return int(total_q.scalar() or 0)


async def list_completed_audits(
    session: AsyncSession,
    *,
    limit: int = _DEFAULT_LIST_LIMIT,
    offset: int = 0,
) -> list[AuditListItem]:
    bounded_limit = max(1, min(limit, _MAX_LIST_LIMIT))
    bounded_offset = max(0, offset)
    result = await session.execute(
        select(Run)
        .where(Run.status == RunStatus.done.value)
        .order_by(Run.created_at.desc())
        .offset(bounded_offset)
        .limit(bounded_limit)
        .options(selectinload(Run.workflow))
    )
    runs = result.scalars().all()
    return [
        run_to_audit_list_item(run, run.workflow.name if run.workflow else "Workflow")
        for run in runs
    ]


async def get_audit_detail(session: AsyncSession, audit_id: str) -> RunAuditDetail | None:
    return await get_run_detail(session, audit_id)
