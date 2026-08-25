"""Shared helpers for audit run phases."""

from __future__ import annotations

from repody.extraction.branding import normalize_public_catalog_id
from repody.extraction.modes import (
    parse_read_path,
    read_path_label,
    validation_mode_label,
)
from repody.infra.db.models import Workflow
from repody.infra.storage.mime import resolve_mime as resolve_storage_mime
from repody.rules.conditions import resolve_rule_body
from repody.util.json_shape import normalize_keys_to_snake

__all__ = [
    "extract_label",
    "meta_to_dict",
    "progress_mode",
    "resolve_upload_mime",
    "rule_dict_from_row",
    "rules_payload",
]


def resolve_upload_mime(declared_mime: str | None, document_bytes: bytes | None) -> str:
    """Prefer the declared upload MIME; sniff only when undeclared."""
    declared = (declared_mime or "").strip()
    if declared:
        return declared
    if document_bytes:
        return resolve_storage_mime(data=document_bytes, declared=None)
    return "application/octet-stream"


def progress_mode(*, has_file: bool) -> str:
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
    """Canonical HTTP/wire shape (camelCase) for extraction meta.

    Used by run_documents.extraction_meta and agentOutcomes handoff payloads.
    Display labels are derived at the edge when absent from the meta object.
    """
    stored_read_label = getattr(meta, "read_path_label", None)
    stored_validation_label = getattr(meta, "validation_label", None)
    read_label = stored_read_label or read_path_label(
        parse_read_path(meta.read_path_used or meta.read_path_config).id
    )
    val_label = stored_validation_label or validation_mode_label(meta.validation_mode)
    return {
        "readPathConfig": meta.read_path_config,
        "readPathUsed": meta.read_path_used,
        "readPathLabel": read_label,
        "validationMode": meta.validation_mode,
        "validationLabel": val_label,
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
        "nativePdf": getattr(meta, "native_pdf", None),
    }


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
