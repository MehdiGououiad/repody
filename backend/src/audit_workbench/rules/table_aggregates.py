"""Aggregate helpers for object-array fields in logic rules."""

from __future__ import annotations

import json
from typing import Any

from audit_workbench.extraction.field_json import parse_numeric_value

LOGIC_TABLE_FUNCTIONS = frozenset({"sum_rows", "sum_rows_where", "count_rows_where"})


def parse_table_rows(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [row for row in raw if isinstance(row, dict)]
    if not isinstance(raw, str):
        return []
    text = raw.strip()
    if not text or text == "—":
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _normalize_column(name: str) -> str:
    return name.strip().lower().replace(" ", "_")


def _row_cell(row: dict[str, Any], column: str) -> str:
    target = _normalize_column(column)
    for key, value in row.items():
        if _normalize_column(str(key)) == target:
            return str(value if value is not None else "").strip()
    return ""


def _row_number(row: dict[str, Any], column: str) -> float | None:
    return parse_numeric_value(_row_cell(row, column))


def sum_rows(table: Any, amount_column: str) -> float:
    total = 0.0
    for row in parse_table_rows(table):
        amount = _row_number(row, amount_column)
        if amount is not None:
            total += amount
    return round(total, 2)


def sum_rows_where(table: Any, amount_column: str, filter_column: str, contains: str) -> float:
    needle = (contains or "").strip().upper()
    total = 0.0
    for row in parse_table_rows(table):
        if needle and needle not in _row_cell(row, filter_column).upper():
            continue
        amount = _row_number(row, amount_column)
        if amount is not None:
            total += amount
    return round(total, 2)


def count_rows_where(table: Any, filter_column: str, contains: str) -> int:
    needle = (contains or "").strip().upper()
    count = 0
    for row in parse_table_rows(table):
        if needle and needle not in _row_cell(row, filter_column).upper():
            continue
        count += 1
    return count
