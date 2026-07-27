"""Parse NuExtract JSON into schema-shaped extracted fields."""

from __future__ import annotations

import json
import re
from typing import Any

from audit_workbench.extraction.nuextract import normalize_template_type
from audit_workbench.extraction.schema import iter_extraction_leaves
from audit_workbench.extraction.template_types import resolve_template_type
from audit_workbench.extraction.types import ExtractedFieldResult, SchemaFieldSpec
from audit_workbench.rules.value_coercion import is_iso_date_like

_NUMERIC_RUN = re.compile(r"[+-]?[\d][\d\s.,]*")
_NUMERIC_TYPES = frozenset({"integer", "number"})


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _resolved_type(spec: SchemaFieldSpec | None) -> str:
    if not spec:
        return "string"
    return resolve_template_type(spec.name, spec.description, spec.template_type)


def _is_numeric_field(spec: SchemaFieldSpec | None) -> bool:
    """Normalize amounts only for explicit/inferred number|integer — not by name glue."""
    if not spec:
        return False
    return normalize_template_type(_resolved_type(spec)) in _NUMERIC_TYPES


def _locale_normalize_numeric(token: str) -> str:
    s = token.strip().replace("\u00a0", " ").replace(" ", "")
    if not s:
        return s
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        parts = s.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            s = f"{parts[0]}.{parts[1]}"
        else:
            s = s.replace(",", ".")
    return s


def normalize_amount(value: str) -> str:
    """Normalize locale-formatted amounts (e.g. '6 000,00 DhTTC') to '6000.00' for rules."""
    s = value.strip()
    if not s or s == "—":
        return s
    match = _NUMERIC_RUN.search(s.replace("\u00a0", " "))
    if not match:
        return s
    return _locale_normalize_numeric(match.group(0))


def parse_numeric_value(value: str) -> float | None:
    """Parse a numeric field value, ignoring trailing currency labels."""
    s = value.strip()
    if not s or s == "—":
        return None
    if is_iso_date_like(s):
        return None
    match = _NUMERIC_RUN.search(s.replace("\u00a0", " "))
    if not match:
        return None
    start, end = match.span()
    prefix = s[:start].strip()
    # Reject alphanumeric IDs like PO-2024-991 where digits sit inside a reference token.
    if prefix and re.search(r"[A-Za-z]", prefix):
        return None
    normalized = normalize_amount(s)
    if not normalized or normalized == "—":
        return None
    try:
        if re.match(r"^-?\d+(\.\d+)?$", normalized):
            return float(normalized)
    except ValueError:
        pass
    return None


def _load_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
    return {}


def parse_fields_json(raw: str, schema: list[SchemaFieldSpec]) -> list[ExtractedFieldResult]:
    leaves = iter_extraction_leaves(schema)
    expected = {_normalize_key(key): (key, spec) for key, spec in leaves}
    payload = _load_json_object(raw)
    rows: list[dict[str, Any]] = payload.get("fields", []) if isinstance(payload, dict) else []

    by_name: dict[str, ExtractedFieldResult] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        norm = _normalize_key(name)
        matched = expected.get(norm)
        display = matched[0] if matched else name
        spec = matched[1] if matched else None
        raw_value = row.get("value")
        # Official NuExtract returns null when a field is missing — treat as not extracted.
        if raw_value is None:
            value = "—"
            extracted = False
        else:
            value = str(raw_value).strip() or "—"
            extracted = value != "—"
        conf = row.get("confidence")
        # NuExtract does not emit confidence — never invent a score.
        confidence = float(conf) if conf is not None else None
        if _is_numeric_field(spec) and extracted and not value.startswith("["):
            value = normalize_amount(value)
        by_name[norm] = ExtractedFieldResult(
            key=display,
            description=spec.description if spec else "",
            value=value,
            type=_resolved_type(spec),
            confidence=confidence,
            extracted=extracted,
        )

    results: list[ExtractedFieldResult] = []
    for key, spec in leaves:
        norm = _normalize_key(key)
        hit = by_name.get(norm)
        if hit:
            results.append(hit)
        else:
            results.append(
                ExtractedFieldResult(
                    key=key,
                    description=spec.description,
                    value="—",
                    type=_resolved_type(spec),
                    confidence=None,
                    extracted=False,
                )
            )
    return results
