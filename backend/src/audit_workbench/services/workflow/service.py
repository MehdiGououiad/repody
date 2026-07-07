from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Document, Workflow, WorkflowStatus
from audit_workbench.schemas.workflow import WorkflowSchema
from audit_workbench.services.mappers import workflow_to_list_schema, workflow_to_schema
from audit_workbench.services.workflow.deployment import deploy_workflow
from audit_workbench.services.workflow.repository import (
    load_workflow,
    short_id,
    upsert_workflow_aggregate,
)
from audit_workbench.services.workflow.stats import (
    batch_workflow_api_stats,
    batch_workflow_stats,
    workflow_api_stats,
    workflow_stats,
)
from audit_workbench.services.workflow.validation import validate_workflow_rules, validate_workflow_schema


async def list_workflows(session: AsyncSession) -> list[WorkflowSchema]:
    result = await session.execute(
        select(Workflow)
        .where(Workflow.status != WorkflowStatus.archived.value)
        .order_by(Workflow.updated_at.desc())
    )
    workflows = result.scalars().all()
    if not workflows:
        return []

    workflow_ids = [wf.id for wf in workflows]
    stats = await batch_workflow_stats(session, workflow_ids)
    deployed_ids = [wf.id for wf in workflows if wf.deployed_at]
    api_stats_by_id = await batch_workflow_api_stats(session, deployed_ids)

    out: list[WorkflowSchema] = []
    for wf in workflows:
        total, rate, last = stats.get(wf.id, (0, 0.0, None))
        api_stats = api_stats_by_id.get(wf.id) if wf.deployed_at else None
        out.append(
            workflow_to_list_schema(
                wf,
                total_runs=total,
                success_rate=rate,
                last_run=last,
                api_stats=api_stats,
            )
        )
    return out


async def get_workflow(session: AsyncSession, workflow_id: str) -> WorkflowSchema | None:
    wf = await load_workflow(session, workflow_id)
    if not wf or wf.status == WorkflowStatus.archived.value:
        return None
    total, rate, last = await workflow_stats(session, workflow_id)
    api_stats = await workflow_api_stats(session, workflow_id) if wf.deployed_at else None
    return workflow_to_schema(
        wf,
        total_runs=total,
        success_rate=rate,
        last_run=last,
        api_stats=api_stats,
    )


async def create_workflow(
    session: AsyncSession,
    *,
    name: str,
    description: str,
    owner: str,
) -> WorkflowSchema:
    wf_id = f"wf-{short_id()}"
    wf = Workflow(
        id=wf_id,
        name=name or "Untitled workflow",
        description=description,
        status=WorkflowStatus.draft.value,
        owner=owner,
    )
    session.add(wf)
    doc = Document(id=f"doc-{short_id()}", workflow_id=wf_id, document_type="", position=0)
    session.add(doc)
    await session.flush()
    wf_loaded = await load_workflow(session, wf_id)
    assert wf_loaded
    return workflow_to_schema(wf_loaded)


async def upsert_workflow(session: AsyncSession, payload: WorkflowSchema) -> WorkflowSchema:
    wf = await load_workflow(session, payload.id)
    if not wf:
        try:
            async with session.begin_nested():
                session.add(
                    Workflow(
                        id=payload.id,
                        name=payload.name,
                        description=payload.description,
                        status=payload.status,
                        owner=payload.owner,
                    )
                )
                await session.flush()
        except IntegrityError:
            pass
        wf = await load_workflow(session, payload.id)
        if not wf:
            raise ValueError(f"Workflow {payload.id} could not be created or loaded")

    validate_workflow_rules(payload)
    validate_workflow_schema(payload)
    await upsert_workflow_aggregate(session, wf, payload)

    wf_loaded = await load_workflow(session, wf.id)
    assert wf_loaded
    total, rate, last = await workflow_stats(session, wf.id)
    return workflow_to_schema(wf_loaded, total_runs=total, success_rate=rate, last_run=last)


SEED_WORKFLOW_ID = "wf-invoice-audit"


async def archive_workflow(session: AsyncSession, workflow_id: str) -> bool:
    if workflow_id == SEED_WORKFLOW_ID:
        return False
    wf = await session.get(Workflow, workflow_id)
    if not wf:
        return False
    wf.status = WorkflowStatus.archived.value
    return True


async def bulk_archive_workflows(session: AsyncSession, workflow_ids: list[str]) -> int:
    archived = 0
    for workflow_id in workflow_ids:
        if await archive_workflow(session, workflow_id):
            archived += 1
    return archived


__all__ = [
    "SEED_WORKFLOW_ID",
    "archive_workflow",
    "bulk_archive_workflows",
    "create_workflow",
    "deploy_workflow",
    "get_workflow",
    "list_workflows",
    "upsert_workflow",
]
