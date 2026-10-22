"""Vocabulary shared by logic-rule authoring checks and evaluation."""

from __future__ import annotations

import re
from typing import Any

from repody.rules.table_aggregates import count_rows_where, sum_rows, sum_rows_where

IDENTIFIER = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")

LOGIC_FUNCTIONS: dict[str, Any] = {
    "sum_rows": sum_rows,
    "sum_rows_where": sum_rows_where,
    "count_rows_where": count_rows_where,
}

# Tokens that look like identifiers but are never field names.
RESERVED_NAMES = frozenset(
    {"and", "or", "not", "True", "False", "None", "if", "else", "in", "is", "str"}
    | set(LOGIC_FUNCTIONS)
)


def normalize_field_key(name: str) -> str:
    """Field names as rules see them: trimmed, lower-case, spaces as underscores."""
    return name.strip().lower().replace(" ", "_")


def field_identifiers(expression: str) -> list[str]:
    """Identifier tokens in ``expression`` that may refer to fields (reserved names removed)."""
    return [token for token in IDENTIFIER.findall(expression) if token not in RESERVED_NAMES]
