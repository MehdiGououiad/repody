from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.db.models import Document, Workflow, WorkflowStatus
from repody.schemas.workflow import WorkflowSchema
from repody.app.mappers import workflow_to_list_schema, workflow_to_schema
from repody.app.workflow.deployment import deploy_workflow
from repody.app.workflow.repository import (
    load_workflow,
    short_id,
    upsert_workflow_aggregate,
)
from repody.app.workflow.stats import (
    batch_workflow_stats,
    workflow_api_stats,
    workflow_stats,
)
from repody.app.workflow.validation import validate_workflow_rules, validate_workflow_schema


async def list_workflows(session: AsyncSession) -> list[WorkflowSchema]:
    """List workflows with lightweight run stats only (no per-workflow API analytics).

    Full ``api_stats`` (series / failing rules / latency) stays on GET detail —
    the UI list never reads those fields and they dominate list latency.
    """
    from sqlalchemy.orm import load_only, noload

    result = await session.execute(
        select(Workflow)
        .where(Workflow.status != WorkflowStatus.archived.value)
        .order_by(Workflow.updated_at.desc())
        .options(
            noload(Workflow.documents),
            noload(Workflow.rules),
            noload(Workflow.runs),
            load_only(
                Workflow.id,
                Workflow.name,
                Workflow.description,
                Workflow.status,
                Workflow.owner,
                Workflow.deployed_at,
                Workflow.api_key_hint,
                Workflow.updated_at,
            ),
        )
    )
    workflows = result.scalars().all()
    if not workflows:
        return []

    workflow_ids = [wf.id for wf in workflows]
    stats = await batch_workflow_stats(session, workflow_ids)

    out: list[WorkflowSchema] = []
    for wf in workflows:
        total, rate, last = stats.get(wf.id, (0, 0.0, None))
        out.append(
            workflow_to_list_schema(
                wf,
                total_runs=total,
                success_rate=rate,
                last_run=last,
                api_stats=None,
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
