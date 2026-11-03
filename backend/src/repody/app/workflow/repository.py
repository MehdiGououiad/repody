"""Workflow aggregate persistence (documents + rules upsert)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, noload, selectinload

from repody.extraction.types import SchemaFieldSpec
from repody.infra.db.models import Document, SchemaField, Workflow, WorkflowRule, WorkflowStatus
from repody.rules.conditions import resolve_rule_body
from repody.schemas.workflow import SchemaFieldSchema, WorkflowSchema
from repody.util.json_shape import normalize_keys_to_snake


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


async def list_workflow_cards(session: AsyncSession) -> list[Workflow]:
    """Load non-archived workflows for list cards (no nested documents/rules/runs)."""
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
    return list(result.scalars().all())


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


def _schema_field_columns(field: SchemaFieldSchema) -> tuple[str, dict | None]:
    """`(template_type, field_config)` columns; children at any depth go in field_config."""
    spec = SchemaFieldSpec.model_validate(field.model_dump())
    template_type = spec.template_type
    if spec.children and template_type not in ("object", "object-array"):
        template_type = "object"
    config = spec.model_dump(include={"enum_values", "children"}, exclude_none=True)
    return template_type, config or None


async def _upsert_documents(session: AsyncSession, wf: Workflow, payload: WorkflowSchema) -> None:
    existing = {doc.id: doc for doc in wf.documents}
    keep_ids: set[str] = set()
    for di, doc in enumerate(payload.documents):
        doc_id = doc.id or f"doc-{short_id()}"
        keep_ids.add(doc_id)
        row = existing.get(doc_id)
        if row:
            row.document_type = doc.document_type
            row.position = di
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
            template_type, field_config = _schema_field_columns(field)
            existing_field = await session.get(SchemaField, field_id)
            if existing_field is not None and existing_field.document_id != doc_id:
                field_id = f"f-{short_id()}"
            session.add(
                SchemaField(
                    id=field_id,
                    document_id=doc_id,
                    name=field.name,
                    description=field.description,
                    template_type=template_type,
                    field_config=field_config,
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
