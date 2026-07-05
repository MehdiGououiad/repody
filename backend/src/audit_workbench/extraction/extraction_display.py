"""Shared extraction progress labels for plan and completed steps."""

from __future__ import annotations

from typing import Any

from audit_workbench.extraction.document_model_branding import public_document_model_label
from audit_workbench.extraction.document_modes import DEFAULT_READ_PATH_ID, parse_read_path, validation_mode_label


def _doc_value(doc: Any, key: str, default: Any = None) -> Any:
    value = getattr(doc, key, None)
    if value is not None:
        return value
    if isinstance(doc, dict):
        return doc.get(key, default)
    return default


def plan_extraction_detail(
    doc: Any,
    *,
    has_file: bool,
    run_validation_mode: str,
) -> str:
    if not has_file:
        return "Schema placeholders (no file uploaded)"
    read_spec = parse_read_path(_doc_value(doc, "extraction_mode", DEFAULT_READ_PATH_ID))
    ocr = _doc_value(doc, "document_model_id")
    parts = [
        f"Read: {read_spec.label}",
        f"Validation: {validation_mode_label(run_validation_mode)}",
    ]
    if ocr and read_spec.show_document_model:
        parts.append(f"Model: {public_document_model_label(ocr)}")
    return " · ".join(parts)


def completed_extraction_detail(meta) -> str:
    parts = [
        f"Engine: {meta.read_path_label}",
        f"Validation: {meta.validation_label}",
    ]
    if meta.document_model_id:
        parts.append(f"Model: {public_document_model_label(meta.document_model_id)}")
    if meta.cache_hit:
        parts.insert(
            0,
            "Same document as a previous run — reusing cached extraction (skipped OCR/LLM)",
        )
    if meta.gpu_cold_start_likely:
        parts.append("Slow extraction may include GPU warm-up (first request after idle)")
    if meta.pages_dropped and meta.pages_rendered:
        parts.append(
            f"Warning: only {meta.pages_sent} of {meta.pages_rendered} page(s) sent to the model"
        )
    parts.append(f"{meta.fields_extracted} field(s) in {meta.extraction_ms}ms")
    return " · ".join(parts)
