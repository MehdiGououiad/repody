from __future__ import annotations

import re

RuleStatus = str  # passed | failed | skipped | error

FEE_KEYWORDS = re.compile(
    r"late\s*fee|penalty|p\u00e9nalit\u00e9|penalite|retard|frais\s+de\s+retard",
    re.I,
)
FIELD_REFERENCE = re.compile(r"(?<![\w@])@([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")


def referenced_fields(body: str) -> list[str]:
    return list(dict.fromkeys(FIELD_REFERENCE.findall(body or "")))


def rule_field_values(
    body: str,
    field_values: dict[str, str],
) -> tuple[dict[str, str], list[str]]:
    references = referenced_fields(body)
    if not references:
        return field_values, []
    selected: dict[str, str] = {}
    missing: list[str] = []
    for reference in references:
        value = field_values.get(reference)
        if value is None:
            value = field_values.get(reference.lower())
        if value is None:
            missing.append(reference)
        else:
            selected[reference] = value
    return selected, missing


def evaluate_fee_keyword_rule(
    body: str,
    field_values: dict[str, str],
) -> tuple[RuleStatus, str] | None:
    if not FEE_KEYWORDS.search(body):
        return None
    for value in field_values.values():
        if value and value != "\u2014" and FEE_KEYWORDS.search(value):
            return "failed", "Possible late-fee or penalty wording found in extracted field values."
    return "passed", "No late-fee or penalty keywords found in extracted values."


def unknown_reference_detail(missing_fields: list[str]) -> str:
    missing = ", ".join(f"@{name}" for name in missing_fields)
    return f"Unknown field reference(s): {missing}."
