"""Workflow aggregate persistence (documents + rules upsert)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from audit_workbench.db.models import Document, SchemaField, Workflow, WorkflowRule
from audit_workbench.extraction.document_modes import normalize_document_modes
from audit_workbench.catalog.registry import normalize_model_id
from audit_workbench.extraction.nuextract_types import normalize_template_type
from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.schemas.workflow import WorkflowSchema
from audit_workbench.util.json_shape import normalize_keys_to_snake


def short_id() -> str:
    return uuid.uuid4().hex[:8]


async def load_workflow(session: AsyncSession, workflow_id: str) -> Workflow | None:
    result = await session.execute(
        select(Workflow)
        .where(Workflow.id == workflow_id)
        .options(
            selectinload(Workflow.documents).selectinload(Document.schema_fields),
            selectinload(Workflow.rules),
        )
    )
    return result.scalar_one_or_none()


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

    await _upsert_documents(session, wf, payload)
    await _upsert_rules(session, wf, payload)
    await session.flush()


def _field_config_payload(field) -> dict | None:
    config: dict = {}
    enum_values = getattr(field, "enum_values", None) or []
    if enum_values:
        config["enum_values"] = [str(v).strip() for v in enum_values if str(v).strip()]
    children = getattr(field, "children", None) or []
    child_rows: list[dict] = []
    for child in children:
        name = (getattr(child, "name", None) or "").strip()
        if not name:
            continue
        row = {
            "name": name,
            "description": getattr(child, "description", None) or "",
            "template_type": normalize_template_type(getattr(child, "template_type", None)),
        }
        child_enum = getattr(child, "enum_values", None) or []
        if child_enum:
            row["enum_values"] = [str(v).strip() for v in child_enum if str(v).strip()]
        child_rows.append(row)
    if child_rows:
        config["children"] = child_rows
    return config or None


async def _upsert_documents(session: AsyncSession, wf: Workflow, payload: WorkflowSchema) -> None:
    existing = {doc.id: doc for doc in wf.documents}
    keep_ids: set[str] = set()
    for di, doc in enumerate(payload.documents):
        doc_id = doc.id or f"doc-{short_id()}"
        keep_ids.add(doc_id)
        read_id, val_id = normalize_document_modes(doc.extraction_mode, doc.validation_mode)
        row = existing.get(doc_id)
        document_model_id = normalize_model_id(doc.document_model_id)
        if row:
            row.document_type = doc.document_type
            row.position = di
            row.extraction_mode = read_id
            row.validation_mode = val_id
            row.document_model_id = document_model_id
            row.extraction_instructions = doc.extraction_instructions or ""
            row.markdown_extraction = doc.markdown_extraction
            row.extraction_icl_examples = [
                {"input": ex.input, "output": ex.output}
                for ex in (doc.extraction_icl_examples or [])
                if ex.input.strip() and ex.output.strip()
            ]
            await session.execute(delete(SchemaField).where(SchemaField.document_id == doc_id))
        else:
            row = Document(
                id=doc_id,
                workflow_id=wf.id,
                document_type=doc.document_type,
                position=di,
                extraction_mode=read_id,
                validation_mode=val_id,
                document_model_id=document_model_id,
                extraction_instructions=doc.extraction_instructions or "",
                markdown_extraction=doc.markdown_extraction,
                extraction_icl_examples=[
                    {"input": ex.input, "output": ex.output}
                    for ex in (doc.extraction_icl_examples or [])
                    if ex.input.strip() and ex.output.strip()
                ],
            )
            session.add(row)
            await session.flush()
        for fi, field in enumerate(doc.schema_fields):
            field_id = field.id or f"f-{short_id()}"
            existing_field = await session.get(SchemaField, field_id)
            if existing_field is not None and existing_field.document_id != doc_id:
                field_id = f"f-{short_id()}"
            session.add(
                SchemaField(
                    id=field_id,
                    document_id=doc_id,
                    name=field.name,
                    description=field.description,
                    template_type=normalize_template_type(field.template_type),
                    field_config=_field_config_payload(field),
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
        rule_id = rule.id or f"r-{short_id()}"
        existing_rule = await session.get(WorkflowRule, rule_id)
        if existing_rule is not None and existing_rule.workflow_id != wf.id:
            rule_id = f"r-{short_id()}"
        keep_ids.add(rule_id)
        normalized_conditions = (
            normalize_keys_to_snake(rule.conditions) if rule.conditions else rule.conditions
        )
        resolved_body = resolve_rule_body(
            {
                "kind": rule.kind,
                "body": rule.body,
                "conditions": normalized_conditions,
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
            row.conditions = normalized_conditions
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
                    conditions=normalized_conditions,
                    condition_junction=rule.condition_junction,
                    position=ri,
                )
            )
    for rule_id, row in existing.items():
        if rule_id not in keep_ids:
            await session.delete(row)
