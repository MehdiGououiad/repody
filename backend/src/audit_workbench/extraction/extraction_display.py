"""Shared extraction progress labels for plan and completed steps."""

from __future__ import annotations

from typing import Any

from audit_workbench.extraction.document_model_branding import public_document_model_label
from audit_workbench.extraction.document_modes import parse_read_path, validation_mode_label


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
    read_spec = parse_read_path(_doc_value(doc, "extraction_mode", "auto"))
    ocr = _doc_value(doc, "ocr_model")
    parts = [
        f"Read: {read_spec.label}",
        f"Validation: {validation_mode_label(run_validation_mode)}",
    ]
    if ocr and read_spec.show_ocr_model:
        parts.append(f"Model: {public_document_model_label(ocr)}")
    return " · ".join(parts)


def completed_extraction_detail(meta) -> str:
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
        parts.append("Slow extraction may include GPU warm-up (first request after idle)")
    parts.append(f"{meta.fields_extracted} field(s) in {meta.extraction_ms}ms")
    return " · ".join(parts)
