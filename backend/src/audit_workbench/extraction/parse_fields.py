from __future__ import annotations

import json
import re
from typing import Any

from audit_workbench.extraction.base import ExtractedFieldResult, SchemaFieldSpec


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def build_extraction_prompt(schema: list[SchemaFieldSpec], document_type: str) -> str:
    """Instructions for the small LLM that maps document text → schema fields."""
    field_lines: list[str] = []
    for field in schema:
        if not field.name.strip():
            continue
        if field.description.strip():
            field_lines.append(f'- "{field.name}": {field.description.strip()}')
        else:
            field_lines.append(f'- "{field.name}"')
    fields_block = "\n".join(field_lines) if field_lines else "- (all structured fields present in the text)"
    doc_hint = document_type.strip() or "document"
    if len(field_lines) <= 5:
        return (
            f"Extract fields from this {doc_hint}. Return JSON only:\n"
            f'{{"fields":[{{"name":"<exact name>","value":"<text>","confidence":0.9}}]}}\n'
            f"Fields:\n{fields_block}\n"
            'Missing → "—". Amounts: digits and decimal only.'
        )
    return (
        f"You extract structured fields from a {doc_hint}.\n"
        f"Return values for these fields (exact names):\n{fields_block}\n"
        "Use each field description to locate the correct value in the document text.\n"
        "For multi-page documents, pages are marked --- Page N ---; use values from any page.\n"
        "Output JSON only:\n"
        '{"fields":[{"name":"<exact field name>","value":"<text>","confidence":0.9}]}\n'
        'Use "—" when a field is missing. For monetary amounts, output digits and decimal '
        "point only (no currency codes or labels like Dh, EUR, TTC)."
    )


def build_extraction_user_message(
    raw_text: str,
    schema: list[SchemaFieldSpec],
    document_type: str,
    *,
    max_chars: int,
) -> str:
    prompt = build_extraction_prompt(schema, document_type)
    body = raw_text.strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n…[truncated]"
    return f"{prompt}\n\n--- DOCUMENT TEXT ---\n{body}"


def build_combined_extraction_user_message(
    raw_text: str,
    schema: list[SchemaFieldSpec],
    document_type: str,
    llm_rules: list[dict],
    *,
    max_chars: int,
) -> str:
    prompt = build_extraction_prompt(schema, document_type)
    rules_block = "\n".join(
        f'- id="{r.get("id")}": {r.get("name")} — {(r.get("body") or "").strip()}'
        for r in llm_rules
    )
    combined = (
        f"{prompt}\n\n"
        "Also evaluate these audit rules against the extracted field values:\n"
        f"{rules_block}\n\n"
        "Output JSON only:\n"
        '{"fields":[{"name":"<exact field name>","value":"<text>","confidence":0.9}],'
        '"rule_results":[{"id":"<rule id>","passed":true|false,"detail":"..."}]}\n'
        'Use "—" when a field is missing. For monetary amounts, output digits and decimal '
        "point only (no currency codes or labels like Dh, EUR, TTC)."
    )
    body = raw_text.strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n…[truncated]"
    return f"{combined}\n\n--- DOCUMENT TEXT ---\n{body}"


def parse_combined_extraction_json(
    raw: str,
    schema: list[SchemaFieldSpec],
    llm_rules: list[dict],
) -> tuple[list[ExtractedFieldResult], dict[str, tuple[str, str]]]:
    payload = _load_json_object(raw)
    fields = parse_fields_json(raw, schema)
    rule_results: dict[str, tuple[str, str]] = {}
    rows = payload.get("rule_results", []) if isinstance(payload, dict) else []
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            rid = str(row["id"])
            if "passed" not in row:
                rule_results[rid] = ("error", 'Missing "passed" in combined LLM result.')
            else:
                passed = bool(row.get("passed"))
                detail = str(row.get("detail") or "")[:500]
                rule_results[rid] = (
                    "passed" if passed else "failed",
                    detail or ("Passed." if passed else "Failed."),
                )
    for rule in llm_rules:
        rid = rule.get("id") or ""
        if rid and rid not in rule_results:
            rule_results[rid] = ("error", "Combined LLM response omitted this rule.")
    return fields, rule_results


# Vision OCR models return document text without an extraction instruction.
VLM_OCR_PROMPT = ""


def looks_like_prompt_echo(text: str) -> bool:
    """Detect when a vision model repeats an extraction prompt instead of OCR output."""
    sample = (text or "").strip()[:400].lower()
    if not sample:
        return False
    markers = (
        "output json only",
        '"fields":[{"name"',
        "return values for these fields",
        "exact field name",
    )
    hits = sum(1 for m in markers if m in sample)
    return hits >= 2


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


def _is_amount_like(spec: SchemaFieldSpec) -> bool:
    blob = f"{spec.name} {spec.description}".lower()
    return any(token in blob for token in _NUMERIC_HINTS)


_NUMERIC_RUN = re.compile(r"[+-]?[\d][\d\s.,]*")


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
    """Parse a numeric field value, ignoring trailing currency labels (e.g. '6000.00DhTTC')."""
    normalized = normalize_amount(value)
    if not normalized or normalized == "—":
        return None
    try:
        if re.match(r"^-?\d+(\.\d+)?$", normalized):
            return float(normalized)
    except ValueError:
        pass
    return None


def _label_tokens(spec: SchemaFieldSpec) -> list[str]:
    tokens: list[str] = []
    for part in (spec.name, spec.description):
        for word in re.split(r"[\s_./-]+", part.lower()):
            word = word.strip()
            if len(word) >= 3 and word not in tokens:
                tokens.append(word)
    return tokens


def _find_labeled_value(text: str, labels: list[str]) -> str | None:
    if not labels:
        return None
    label_set = set(labels)
    best_value: str | None = None
    best_score = 0
    for line in text.splitlines():
        lower = line.lower()
        score = sum(1 for label in labels if label in lower)
        if score == 0:
            continue
        if "ttc" in label_set and "ttc" in lower:
            score += 2
        if "ht" in lower and "ttc" in label_set and "ttc" not in lower:
            score -= 2
        match = _NUMERIC_RUN.search(line.replace("\u00a0", " "))
        if not match or score <= best_score:
            continue
        best_score = score
        best_value = normalize_amount(match.group(0))
    if best_value:
        return best_value
    label_pattern = "|".join(re.escape(label) for label in labels[:6])
    if not label_pattern:
        return None
    pattern = re.compile(
        rf"(?:{label_pattern})[^\d]{{0,40}}([+-]?[\d][\d\s.,]*)",
        re.IGNORECASE,
    )
    match = pattern.search(text.replace("\u00a0", " "))
    if match:
        return normalize_amount(match.group(1))
    return None


def extract_fields_heuristic(
    raw_text: str,
    schema: list[SchemaFieldSpec],
) -> list[ExtractedFieldResult] | None:
    """
    Fast label/regex extraction for digital PDFs — skips LLM when every field is found.
    """
    text = (raw_text or "").strip()
    if not text or not schema:
        return None

    results: list[ExtractedFieldResult] = []
    for spec in schema:
        if not spec.name.strip():
            continue
        labels = _label_tokens(spec)
        value = _find_labeled_value(text, labels)
        amount_like = _is_amount_like(spec)
        if value:
            normalized = normalize_amount(value) if amount_like else value
            results.append(
                ExtractedFieldResult(
                    key=spec.name,
                    description=spec.description,
                    value=normalized,
                    type="currency" if amount_like else "string",
                    confidence=0.92,
                    extracted=True,
                )
            )
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

    if not results or not all(row.extracted for row in results):
        return None
    return results


def extraction_num_ctx(prompt_chars: int, *, max_tokens: int, cap: int) -> int:
    """Size inference context to the prompt."""
    estimated = (prompt_chars // 3) + max_tokens + 64
    return max(512, min(cap, estimated))


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
