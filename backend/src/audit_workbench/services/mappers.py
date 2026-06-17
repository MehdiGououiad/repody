from __future__ import annotations

from datetime import UTC, datetime

from audit_workbench.db.models import Run, Workflow
from audit_workbench.extraction.document_model_branding import normalize_public_catalog_id
from audit_workbench.schemas.audit import AuditListItem
from audit_workbench.schemas.run import (
    RunAuditDetail,
    RunAuditDocument,
    RunAuditField,
    RunAuditMetadata,
    RunAuditRule,
    RunDocumentExtractionMeta,
    RunSummary,
)
from audit_workbench.schemas.workflow import (
    DocumentDefSchema,
    SchemaFieldSchema,
    WorkflowApiStatsSchema,
    WorkflowRuleSchema,
    WorkflowSchema,
)


def _fmt_dt(dt: datetime | None) -> str | None:
    if not dt:
        return None
    return dt.strftime("%b %d, %Y")


def _fmt_dt_iso(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.isoformat()


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def duration_ms_between(start: datetime | None, end: datetime | None) -> int:
    if not start or not end:
        return 0
    return int((_as_utc(end) - _as_utc(start)).total_seconds() * 1000)


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
                extraction_mode=doc.extraction_mode or "auto",
                validation_mode=getattr(doc, "validation_mode", None) or "logic_only",
                ocr_model=normalize_public_catalog_id(doc.ocr_model),
                schema_fields=[
                    SchemaFieldSchema(id=f.id, name=f.name, description=f.description)
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
            conditions=r.conditions,
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
        default_llm_model=wf.default_llm_model,
        api_stats=api_stats,
    )


def run_to_audit_detail(run: Run, workflow_name: str) -> RunAuditDetail:
    documents = []
    for rd in run.documents:
        extraction = None
        if rd.extraction_meta:
            extraction = RunDocumentExtractionMeta.model_validate(rd.extraction_meta)
        documents.append(
            RunAuditDocument(
                id=rd.id,
                document_type=rd.document_type,
                file_name=rd.file_name,
                extraction=extraction,
                fields=[
                    RunAuditField(
                        key=f.key,
                        description=f.description,
                        value=f.value,
                        type=f.type,
                        confidence=f.confidence,
                        extracted=f.extracted,
                        flagged=f.flagged,
                    )
                    for f in rd.fields
                ],
            )
        )
    rule_results = [
        RunAuditRule(
            id=rr.id,
            name=rr.name,
            kind=rr.kind,
            scope=rr.scope,
            status=rr.status,
            severity=rr.severity,
            expression=rr.expression,
            affected_fields=rr.affected_fields or [],
            detail=rr.detail,
            expected_value=rr.expected_value,
            actual_value=rr.actual_value,
        )
        for rr in run.rule_results
    ]
    metadata = None
    if run.run_metadata:
        metadata = RunAuditMetadata.model_validate(run.run_metadata)
    elif run.started_at or run.finished_at:
        duration_ms = duration_ms_between(run.started_at, run.finished_at)
        metadata = RunAuditMetadata(
            started_at=_fmt_dt_iso(run.started_at) or None,
            finished_at=_fmt_dt_iso(run.finished_at) or None,
            duration_ms=duration_ms,
        )
    return RunAuditDetail(
        id=run.id,
        workflow_id=run.workflow_id,
        workflow_name=workflow_name,
        status=run.overall_status or "warning",
        source=run.source,
        created_at=_fmt_dt_iso(run.created_at),
        documents=documents,
        rule_results=rule_results,
        summary=RunSummary(
            total=run.summary_total,
            passed=run.summary_passed,
            failed=run.summary_failed,
            fields_extracted=run.fields_extracted,
        ),
        metadata=metadata,
    )


def run_to_audit_list_item(run: Run, workflow_name: str) -> AuditListItem:
    return AuditListItem(
        id=run.id,
        status=run.overall_status or "warning",
        workflow_id=run.workflow_id,
        workflow_name=workflow_name,
        entity=workflow_name,
        timestamp=_fmt_dt_iso(run.created_at),
        rows=run.fields_extracted,
        failed_rules=run.summary_failed,
    )
