"""Workflow aggregate persistence (documents + rules upsert)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import Document, SchemaField, Workflow, WorkflowRule
from audit_workbench.extraction.model_registry import normalize_model_id
from audit_workbench.extraction.processing_paths import normalize_document_modes
from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.schemas.workflow import WorkflowSchema


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


async def upsert_workflow_aggregate(
    session: AsyncSession,
    wf: Workflow,
    payload: WorkflowSchema,
) -> None:
    """Persist workflow metadata and nested documents/rules."""
    wf.name = payload.name
    wf.description = payload.description
    wf.status = payload.status
    wf.owner = payload.owner
    wf.default_llm_model = payload.default_llm_model

    await _upsert_documents(session, wf, payload)
    await _upsert_rules(session, wf, payload)
    await session.flush()


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
