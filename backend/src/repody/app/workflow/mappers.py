"""Workflow ORM rows -> HTTP schemas."""

from __future__ import annotations

from datetime import datetime

from repody.extraction.types import SchemaFieldSpec
from repody.infra.db.models import Workflow
from repody.schemas.workflow import (
    DocumentDefSchema,
    ExtractionIclExampleSchema,
    SchemaFieldSchema,
    WorkflowApiStatsSchema,
    WorkflowRuleSchema,
    WorkflowSchema,
)
from repody.util.json_shape import normalize_keys_to_snake


def _schema_field_schema(spec: SchemaFieldSpec, field_id: str) -> SchemaFieldSchema:
    return SchemaFieldSchema(
        id=field_id,
        name=spec.name,
        description=spec.description,
        template_type=spec.template_type,
        enum_values=spec.enum_values or [],
        children=[
            _schema_field_schema(child, f"{field_id}-c{i}")
            for i, child in enumerate(spec.children or [])
        ],
    )


def _schema_field_from_orm(field) -> SchemaFieldSchema:
    spec = SchemaFieldSpec.model_validate(
        {
            "name": field.name,
            "description": field.description,
            "template_type": field.template_type,
            "field_config": field.field_config,
        }
    )
    return _schema_field_schema(spec, field.id)


def _fmt_dt(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.strftime("%b %d, %Y")


def workflow_to_list_schema(
    wf: Workflow,
    *,
    total_runs: int = 0,
    success_rate: float = 0.0,
    last_run: str | None = None,
    api_stats: WorkflowApiStatsSchema | None = None,
) -> WorkflowSchema:
    return WorkflowSchema(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        status=wf.status,
        owner=wf.owner,
        last_run=last_run,
        success_rate=success_rate,
        total_runs=total_runs,
        documents=[],
        rules=[],
        deployed_at=_fmt_dt(wf.deployed_at),
        api_key_hint=wf.api_key_hint,
        api_stats=api_stats,
    )


def workflow_to_schema(
    wf: Workflow,
    *,
    total_runs: int = 0,
    success_rate: float = 0.0,
    last_run: str | None = None,
    api_stats: WorkflowApiStatsSchema | None = None,
    reveal_api_key: str | None = None,
) -> WorkflowSchema:
    documents = []
    for doc in sorted(wf.documents, key=lambda d: d.position):
        documents.append(
            DocumentDefSchema(
                id=doc.id,
                document_type=doc.document_type,
                extraction_instructions=doc.extraction_instructions or "",
                markdown_extraction=doc.markdown_extraction,
                extraction_icl_examples=[
                    ExtractionIclExampleSchema(
                        input=str(row.get("input") or ""),
                        output=str(row.get("output") or ""),
                    )
                    for row in (getattr(doc, "extraction_icl_examples", None) or [])
                    if isinstance(row, dict)
                ],
                schema_fields=[
                    _schema_field_from_orm(f)
                    for f in sorted(doc.schema_fields, key=lambda x: x.position)
                ],
            )
        )
    rules = [
        WorkflowRuleSchema(
            id=r.id,
            name=r.name,
            kind=r.kind,
            scope=r.scope,
            applies_to=r.applies_to or [],
            conditions=normalize_keys_to_snake(r.conditions) if r.conditions else r.conditions,
            condition_junction=r.condition_junction,
            body=r.body,
            severity=r.severity,
        )
        for r in sorted(wf.rules, key=lambda x: x.position)
    ]
    return WorkflowSchema(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        status=wf.status,
        owner=wf.owner,
        last_run=last_run,
        success_rate=success_rate,
        total_runs=total_runs,
        documents=documents,
        rules=rules,
        deployed_at=_fmt_dt(wf.deployed_at),
        api_key=reveal_api_key,
        api_key_hint=wf.api_key_hint,
        api_stats=api_stats,
    )
