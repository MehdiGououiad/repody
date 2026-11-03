"""Field values a rule can reference, keyed by canonical name (``field_key``)."""

from __future__ import annotations

from repody.rules.expression import field_key
from repody.rules.types import rule_applies_to


def field_values_from_extractions(
    rows: list[tuple[str, str, str | None]], *, multi_document: bool
) -> dict[str, str]:
    """Rule namespace from extracted ``(key, value, document_type)`` rows.

    In multi-document workflows every field is also reachable as ``<document_type>__<field>``;
    a bare field name is available when exactly one document has it.
    """
    values: dict[str, str] = {}
    bare: dict[str, list[str]] = {}
    for key, value, doc_type in rows:
        if not key or not value:
            continue
        if multi_document and doc_type:
            values[field_key(f"{doc_type}.{key}")] = value
        bare.setdefault(field_key(key), []).append(value)
    for key, found in bare.items():
        if not multi_document or len(found) == 1:
            values[key] = found[-1]
    return values


def field_values_for_rule(
    rows: list[tuple[str, str, str | None]],
    rule: dict,
    *,
    doc_types_by_id: dict[str, str],
    multi_document: bool,
) -> dict[str, str]:
    """Namespace limited to the documents the rule applies to (all when unset)."""
    if not multi_document:
        return field_values_from_extractions(rows, multi_document=False)
    allowed = {
        doc_types_by_id[doc_id] for doc_id in rule_applies_to(rule) if doc_id in doc_types_by_id
    }
    if allowed:
        rows = [row for row in rows if row[2] in allowed]
    return field_values_from_extractions(rows, multi_document=True)
