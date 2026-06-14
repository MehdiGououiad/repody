"""Shared helpers for audit run phases."""

from __future__ import annotations

import uuid

from audit_workbench.db.models import RunDocument, Workflow
from audit_workbench.extraction.document_model_branding import (
    normalize_public_catalog_id,
    public_document_model_label,
)
from audit_workbench.rules.conditions import resolve_rule_body
from audit_workbench.storage.mime import resolve_mime as resolve_storage_mime


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
        "ocrModel": normalize_public_catalog_id(meta.ocr_model),
        "llmModel": meta.llm_model,
        "extractionMs": meta.extraction_ms,
        "combinedLlm": meta.combined_llm,
        "cacheHit": meta.cache_hit,
        "gpuColdStartLikely": meta.gpu_cold_start_likely,
        "fieldsExtracted": meta.fields_extracted,
        "ocrText": meta.ocr_text,
        "ocrSkipped": meta.ocr_skipped,
    }


def extraction_step_detail(meta) -> str:
    parts = [
        f"Engine: {meta.read_path_label}",
        f"Validation: {meta.validation_label}",
    ]
    if meta.ocr_model:
        parts.append(f"Model: {public_document_model_label(meta.ocr_model)}")
    if meta.combined_llm:
        parts.append("Combined extract + LLM validation")
    if meta.cache_hit:
        parts.insert(
            0,
            "Same document as a previous run — reusing cached extraction (skipped OCR/LLM)",
        )
    if meta.gpu_cold_start_likely:
        parts.append(
            "Slow extraction may include GPU warm-up (first request after idle)"
        )
    parts.append(f"{meta.fields_extracted} field(s) in {meta.extraction_ms}ms")
    return " · ".join(parts)


def rules_payload(workflow: Workflow) -> list[dict]:
    return [
        {
            "id": r.id,
            "name": r.name,
            "kind": r.kind,
            "scope": r.scope,
            "body": resolve_rule_body(
                {
                    "body": r.body,
                    "conditions": r.conditions,
                    "condition_junction": r.condition_junction,
                }
            ),
            "severity": r.severity,
            "conditions": r.conditions,
            "condition_junction": r.condition_junction,
        }
        for r in sorted(workflow.rules, key=lambda x: x.position)
    ]


def resolve_validation_mode(workflow_docs, rules: list[dict] | None = None) -> str:
    from audit_workbench.extraction.processing_paths import (
        parse_validation_mode,
        resolve_run_validation,
    )
    from audit_workbench.settings import get_settings

    settings = get_settings()
    if settings.llm_validation_enabled and any(
        (rule.get("kind") or "logic").lower() == "llm" for rule in rules or []
    ):
        return "logic_and_llm"

    modes = [
        parse_validation_mode(
            getattr(doc, "validation_mode", None),
            extraction_mode=doc.extraction_mode,
        )
        for doc in workflow_docs
        if any(f.name.strip() for f in doc.schema_fields)
    ]
    return resolve_run_validation(modes)
