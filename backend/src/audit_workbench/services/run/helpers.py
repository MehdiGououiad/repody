"""Shared helpers for audit run phases."""

from __future__ import annotations

import uuid

from audit_workbench.db.models import RunDocument, Workflow
from audit_workbench.extraction.document_model_branding import normalize_public_catalog_id
from audit_workbench.extraction.extraction_display import completed_extraction_detail
from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.storage.mime import resolve_mime as resolve_storage_mime
from audit_workbench.util.json_shape import normalize_keys_to_snake


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def resolve_run_doc_mime(run_doc: RunDocument, document_bytes: bytes | None) -> str:
    if run_doc.mime_type:
        if document_bytes:
            return resolve_storage_mime(data=document_bytes, declared=run_doc.mime_type)
        return run_doc.mime_type
    if document_bytes:
        return resolve_storage_mime(data=document_bytes, declared=None)
    return "application/octet-stream"


def progress_mode(doc, *, has_file: bool) -> str:
    if not has_file:
        return "schema"
    return "document_model"


def extract_label(doc_type: str, *, mode: str, detail: str | None = None) -> str:
    labels = {
        "schema": f"Schema placeholders for {doc_type}…",
        "document_model": f"Document model extraction · {doc_type}…",
    }
    base = labels.get(mode, f"Extracting {doc_type}…")
    return f"{base} ({detail})" if detail else base


def meta_to_dict(meta) -> dict:
    return {
        "readPathConfig": meta.read_path_config,
        "readPathUsed": meta.read_path_used,
        "readPathLabel": meta.read_path_label,
        "validationMode": meta.validation_mode,
        "validationLabel": meta.validation_label,
        "documentModelId": normalize_public_catalog_id(meta.document_model_id),
        "extractionMs": meta.extraction_ms,
        "cacheHit": meta.cache_hit,
        "gpuColdStartLikely": meta.gpu_cold_start_likely,
        "fieldsExtracted": meta.fields_extracted,
        "markdownExtraction": meta.markdown_extraction,
        "markdownText": meta.markdown_text,
        "rawText": meta.raw_text,
        "pagesRendered": meta.pages_rendered,
        "pagesSent": meta.pages_sent,
        "pagesDropped": meta.pages_dropped,
    }


def extraction_step_detail(meta) -> str:
    return completed_extraction_detail(meta)


def rule_dict_from_row(
    *,
    rule_id: str,
    name: str,
    kind: str,
    scope: str,
    applies_to: list | None,
    body: str,
    severity: str,
    conditions,
    condition_junction,
) -> dict:
    normalized_conditions = normalize_keys_to_snake(conditions) if conditions else conditions
    return {
        "id": rule_id,
        "name": name,
        "kind": kind,
        "scope": scope,
        "applies_to": applies_to or [],
        "body": resolve_rule_body(
            {
                "body": body,
                "conditions": normalized_conditions,
                "condition_junction": condition_junction,
            }
        ),
        "severity": severity,
        "conditions": normalized_conditions,
        "condition_junction": condition_junction,
    }


def rules_payload(workflow: Workflow) -> list[dict]:
    return [
        rule_dict_from_row(
            rule_id=r.id,
            name=r.name,
            kind=r.kind,
            scope=r.scope,
            applies_to=r.applies_to,
            body=r.body,
            severity=r.severity,
            conditions=r.conditions,
            condition_junction=r.condition_junction,
        )
        for r in sorted(workflow.rules, key=lambda x: x.position)
    ]
