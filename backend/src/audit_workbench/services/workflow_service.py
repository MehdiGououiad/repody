from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.db.models import Document, SchemaField, Workflow, WorkflowRule, WorkflowStatus
from audit_workbench.schemas.workflow import WorkflowSchema
from audit_workbench.rules.validation import validate_rule_dict
from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.extraction.model_registry import normalize_model_id
from audit_workbench.extraction.processing_paths import normalize_document_modes
from audit_workbench.services.api_keys import api_key_hint, hash_api_key
from audit_workbench.settings import get_settings
from audit_workbench.services.mappers import load_workflow, workflow_to_schema
from audit_workbench.services.workflow_stats import batch_workflow_stats, workflow_api_stats


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


def _validate_rules(payload: WorkflowSchema) -> None:
    for rule in payload.rules:
        resolved_body = resolve_rule_body(
            {
                "body": rule.body,
                "conditions": rule.conditions,
                "condition_junction": rule.condition_junction,
            }
        )
        rule_errors = validate_rule_dict(
            {
                "id": rule.id,
                "name": rule.name,
                "kind": rule.kind,
                "body": resolved_body,
            }
        )
        if rule_errors:
            raise ValueError("; ".join(rule_errors))


async def list_workflows(session: AsyncSession) -> list[WorkflowSchema]:
    result = await session.execute(
        select(Workflow)
        .where(Workflow.status != WorkflowStatus.archived.value)
        .options(
            selectinload(Workflow.documents).selectinload(Document.schema_fields),
            selectinload(Workflow.rules),
        )
        .order_by(Workflow.updated_at.desc())
    )
    workflows = result.scalars().all()
    stats = await batch_workflow_stats(session, [wf.id for wf in workflows])
    out: list[WorkflowSchema] = []
    for wf in workflows:
        total, rate, last = stats.get(wf.id, (0, 0.0, None))
        api_stats = await workflow_api_stats(session, wf.id) if wf.deployed_at else None
        out.append(
            workflow_to_schema(
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
    from audit_workbench.services.mappers import workflow_stats

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
    wf_id = f"wf-{_short_id()}"
    wf = Workflow(
        id=wf_id,
        name=name or "Untitled workflow",
        description=description,
        status=WorkflowStatus.draft.value,
        owner=owner,
    )
    session.add(wf)
    doc = Document(id=f"doc-{_short_id()}", workflow_id=wf_id, document_type="", position=0)
    session.add(doc)
    await session.flush()
    wf_loaded = await load_workflow(session, wf_id)
    assert wf_loaded
    return workflow_to_schema(wf_loaded)


async def _upsert_documents(session: AsyncSession, wf: Workflow, payload: WorkflowSchema) -> None:
    existing = {doc.id: doc for doc in wf.documents}
    keep_ids: set[str] = set()
    for di, doc in enumerate(payload.documents):
        doc_id = doc.id or f"doc-{_short_id()}"
        keep_ids.add(doc_id)
        read_id, val_id = normalize_document_modes(doc.extraction_mode, doc.validation_mode)
        row = existing.get(doc_id)
        ocr_id = normalize_model_id(doc.ocr_model)
        if row:
            row.document_type = doc.document_type
            row.position = di
            row.extraction_mode = read_id
            row.validation_mode = val_id
            row.ocr_model = ocr_id
            await session.execute(
                delete(SchemaField).where(SchemaField.document_id == doc_id)
            )
        else:
            row = Document(
                id=doc_id,
                workflow_id=wf.id,
                document_type=doc.document_type,
                position=di,
                extraction_mode=read_id,
                validation_mode=val_id,
                ocr_model=ocr_id,
            )
            session.add(row)
            await session.flush()
        for fi, field in enumerate(doc.schema_fields):
            field_id = field.id or f"f-{_short_id()}"
            existing_field = await session.get(SchemaField, field_id)
            if existing_field is not None and existing_field.document_id != doc_id:
                field_id = f"f-{_short_id()}"
            session.add(
                SchemaField(
                    id=field_id,
                    document_id=doc_id,
                    name=field.name,
                    description=field.description,
                    position=fi,
                )
            )
    for doc_id, row in existing.items():
        if doc_id not in keep_ids:
            await session.delete(row)


async def _upsert_rules(session: AsyncSession, wf: Workflow, payload: WorkflowSchema) -> None:
    existing = {rule.id: rule for rule in wf.rules}
    keep_ids: set[str] = set()
    for ri, rule in enumerate(payload.rules):
        rule_id = rule.id or f"r-{_short_id()}"
        existing_rule = await session.get(WorkflowRule, rule_id)
        if existing_rule is not None and existing_rule.workflow_id != wf.id:
            rule_id = f"r-{_short_id()}"
        keep_ids.add(rule_id)
        resolved_body = resolve_rule_body(
            {
                "body": rule.body,
                "conditions": rule.conditions,
                "condition_junction": rule.condition_junction,
            }
        )
        row = existing.get(rule_id)
        if row:
            row.name = rule.name
            row.kind = rule.kind
            row.scope = rule.scope
            row.body = resolved_body
            row.severity = rule.severity
            row.applies_to = rule.applies_to
            row.conditions = rule.conditions
            row.condition_junction = rule.condition_junction
            row.position = ri
        else:
            session.add(
                WorkflowRule(
                    id=rule_id,
                    workflow_id=wf.id,
                    name=rule.name,
                    kind=rule.kind,
                    scope=rule.scope,
                    body=resolved_body,
                    severity=rule.severity,
                    applies_to=rule.applies_to,
                    conditions=rule.conditions,
                    condition_junction=rule.condition_junction,
                    position=ri,
                )
            )
    for rule_id, row in existing.items():
        if rule_id not in keep_ids:
            await session.delete(row)


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
                        default_llm_model=payload.default_llm_model,
                    )
                )
                await session.flush()
        except IntegrityError:
            pass
        wf = await load_workflow(session, payload.id)
        if not wf:
            raise ValueError(f"Workflow {payload.id} could not be created or loaded")

    _validate_rules(payload)

    wf.name = payload.name
    wf.description = payload.description
    wf.status = payload.status
    wf.owner = payload.owner
    wf.default_llm_model = payload.default_llm_model

    await _upsert_documents(session, wf, payload)
    await _upsert_rules(session, wf, payload)

    await session.flush()
    wf_loaded = await load_workflow(session, wf.id)
    assert wf_loaded
    from audit_workbench.services.mappers import workflow_stats

    total, rate, last = await workflow_stats(session, wf.id)
    return workflow_to_schema(wf_loaded, total_runs=total, success_rate=rate, last_run=last)


async def deploy_workflow(
    session: AsyncSession,
    workflow_id: str,
    api_key: str | None = None,
) -> WorkflowSchema | None:
    wf = await load_workflow(session, workflow_id)
    if not wf:
        return None
    wf.deployed_at = datetime.now(UTC)
    wf.status = WorkflowStatus.active.value
    raw_key = api_key or f"wbk_live_{secrets.token_hex(16)}"
    wf.api_key = hash_api_key(raw_key)
    wf.api_key_hint = api_key_hint(raw_key)
    await session.flush()
    from audit_workbench.services.mappers import workflow_stats

    total, rate, last = await workflow_stats(session, workflow_id)
    api_stats = await workflow_api_stats(session, workflow_id)
    return workflow_to_schema(
        wf,
        total_runs=total,
        success_rate=rate,
        last_run=last,
        api_stats=api_stats,
        reveal_api_key=raw_key,
    )


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
