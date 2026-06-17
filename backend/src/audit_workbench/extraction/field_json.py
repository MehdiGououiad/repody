"""Parse structured field JSON from document model output."""

from __future__ import annotations

import json
import re
from typing import Any

from audit_workbench.extraction.base import ExtractedFieldResult, SchemaFieldSpec

_NUMERIC_HINTS = (
    "amount",
    "total",
    "montant",
    "tax",
    "fee",
    "price",
    "prix",
    "cost",
    "rate",
    "percent",
    "quantity",
    "qty",
    "sum",
    "balance",
    "ht",
    "ttc",
    "tva",
)
_NUMERIC_RUN = re.compile(r"[+-]?[\d][\d\s.,]*")


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _is_amount_like(spec: SchemaFieldSpec) -> bool:
    blob = f"{spec.name} {spec.description}".lower()
    return any(token in blob for token in _NUMERIC_HINTS)


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
    normalized = normalize_amount(value)
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
    expected = {_normalize_key(f.name): f for f in schema if f.name.strip()}
    payload = _load_json_object(raw)
    rows: list[dict[str, Any]] = payload.get("fields", []) if isinstance(payload, dict) else []

    by_name: dict[str, ExtractedFieldResult] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or row.get("key") or "").strip()
        if not name:
            continue
        norm = _normalize_key(name)
        spec = expected.get(norm)
        display = spec.name if spec else name
        value = str(row.get("value") or row.get("text") or "—").strip() or "—"
        conf = row.get("confidence")
        confidence = float(conf) if conf is not None else (0.85 if value != "—" else None)
        amount_like = _is_amount_like(spec) if spec else False
        normalized = normalize_amount(value) if amount_like and value != "—" else value
        by_name[norm] = ExtractedFieldResult(
            key=display,
            description=spec.description if spec else "",
            value=normalized,
            type="currency" if amount_like else "string",
            confidence=confidence,
            extracted=value != "—",
        )

    results: list[ExtractedFieldResult] = []
    for spec in schema:
        if not spec.name.strip():
            continue
        norm = _normalize_key(spec.name)
        hit = by_name.get(norm)
        if hit:
            results.append(hit)
        else:
            results.append(
                ExtractedFieldResult(
                    key=spec.name,
                    description=spec.description,
                    value="—",
                    type="string",
                    confidence=None,
                    extracted=False,
                )
            )
    return results
