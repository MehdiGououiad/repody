"""Shared helpers for audit run phases."""

from __future__ import annotations

from typing import Any

from repody.infra.db.models import Workflow
from repody.infra.storage.mime import resolve_mime as resolve_storage_mime
from repody.rules.conditions import resolve_rule_body
from repody.util.json_shape import normalize_keys_to_snake

__all__ = [
    "attr_or_key",
    "meta_to_dict",
    "resolve_upload_mime",
    "rule_dict_from_row",
    "rules_payload",
]


def attr_or_key(item: Any, key: str, default: Any = None) -> Any:
    """Read ``key`` from an ORM row / dataclass attribute, or from a dict."""
    value = getattr(item, key, None)
    if value is not None:
        return value
    if isinstance(item, dict):
        return item.get(key, default)
    return default


def resolve_upload_mime(declared_mime: str | None, document_bytes: bytes | None) -> str:
    """Prefer the declared upload MIME; sniff only when undeclared."""
    declared = (declared_mime or "").strip()
    if declared:
        return declared
    if document_bytes:
        return resolve_storage_mime(data=document_bytes, declared=None)
    return "application/octet-stream"


def meta_to_dict(meta) -> dict:
    """Wire shape (camelCase) of extraction meta, stored on run_documents.extraction_meta."""
    return {
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
