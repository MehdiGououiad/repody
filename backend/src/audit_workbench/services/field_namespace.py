from __future__ import annotations


def doc_field_prefix(document_type: str, *, multi_document: bool) -> str:
    """Token prefix for cross-document rules (matches workflow UI)."""
    if not multi_document:
        return ""
    slug = document_type.strip().lower().replace(" ", "_")
    return f"{slug}." if slug else ""


def _with_document_type_aliases(values: dict[str, str], document_types: set[str]) -> dict[str, str]:
    """
    Add dotted (and __) field keys for each document type.

    Multi-document workflows build rule expressions with UI tokens like
    facture1__total even for intra rules scoped to one document; bare keys
    alone are not enough for the logic evaluator.
    """
    if not document_types:
        return values
    out = dict(values)
    for doc_type in document_types:
        prefix = doc_field_prefix(doc_type, multi_document=True)
        if not prefix:
            continue
        for key, val in list(values.items()):
            if "." in key:
                continue
            qualified = f"{prefix}{key}"
            out[qualified] = val
            norm_q = qualified.strip().lower().replace(" ", "_")
            out[norm_q] = val
    return out


def field_values_from_extractions(
    rows: list[tuple[str, str, str | None]],
    *,
    multi_document: bool,
) -> dict[str, str]:
    """
    Build evaluator namespace from extracted rows.

    Each row is (key, value, document_type). When multiple documents exist,
    prefixed keys (e.g. contract.reference_id) are added alongside bare keys when unique.
    """
    values: dict[str, str] = {}
    bare_keys: dict[str, list[str]] = {}

    for key, value, doc_type in rows:
        if not key or not value:
            continue
        prefix = doc_field_prefix(doc_type or "", multi_document=multi_document)
        qualified = f"{prefix}{key}" if prefix else key
        values[qualified] = value
        norm_q = qualified.strip().lower().replace(" ", "_")
        values[norm_q] = value

        bare_keys.setdefault(key, []).append(value)
        if not prefix:
            values[key] = value
            norm = key.strip().lower().replace(" ", "_")
            values[norm] = value

    if multi_document:
        for key, vals in bare_keys.items():
            if len(vals) == 1:
                values[key] = vals[0]
                norm = key.strip().lower().replace(" ", "_")
                values[norm] = vals[0]

    return values


def _rule_applies_to(rule: dict) -> list[str]:
    raw = rule.get("applies_to") or rule.get("appliesTo") or []
    return [str(doc_id) for doc_id in raw if doc_id]


def field_values_for_rule(
    rows: list[tuple[str, str, str | None]],
    rule: dict,
    *,
    doc_types_by_id: dict[str, str],
    multi_document: bool,
) -> dict[str, str]:
    """
    Build field namespace scoped to a rule's appliesTo documents.

    Intra rules on one document in a multi-document workflow must see bare field
    keys (e.g. total) even when the same key exists on other documents.
    """
    if not multi_document:
        return field_values_from_extractions(rows, multi_document=False)

    scope = (rule.get("scope") or "intra").lower()
    applies_to = _rule_applies_to(rule)

    if scope == "cross" and len(applies_to) >= 2:
        allowed = {doc_types_by_id[doc_id] for doc_id in applies_to if doc_id in doc_types_by_id}
        filtered = [row for row in rows if row[2] in allowed]
        return field_values_from_extractions(filtered, multi_document=True)

    if applies_to:
        allowed = {doc_types_by_id[doc_id] for doc_id in applies_to if doc_id in doc_types_by_id}
        filtered = [row for row in rows if row[2] in allowed]
        if len(allowed) == 1:
            values = field_values_from_extractions(filtered, multi_document=False)
            return _with_document_type_aliases(values, allowed)
        if allowed:
            return field_values_from_extractions(filtered, multi_document=True)

    return field_values_from_extractions(rows, multi_document=True)
