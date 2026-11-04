"""Sum and count rows of an object-array field (stored as a JSON list of objects)."""

from __future__ import annotations

import json
from typing import Any

from repody.rules.values import field_key, parse_numeric_value


def _rows(raw: str | None) -> list[dict[str, Any]]:
    try:
        data = json.loads(raw or "")
    except json.JSONDecodeError:
        return []
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def _cell(row: dict[str, Any], column: str) -> str:
    target = field_key(column)
    value = next((v for k, v in row.items() if field_key(str(k)) == target), None)
    return "" if value is None else str(value).strip()


def _matching(raw: str | None, filter_column: str, contains: str) -> list[dict[str, Any]]:
    needle = contains.strip().upper()
    return [row for row in _rows(raw) if not needle or needle in _cell(row, filter_column).upper()]


def sum_rows(
    raw: str | None, amount_column: str, filter_column: str = "", contains: str = ""
) -> float:
    amounts = (
        parse_numeric_value(_cell(row, amount_column))
        for row in _matching(raw, filter_column, contains)
    )
    return round(sum(a for a in amounts if a is not None), 2)


def count_rows(raw: str | None, filter_column: str = "", contains: str = "") -> int:
    return len(_matching(raw, filter_column, contains))
