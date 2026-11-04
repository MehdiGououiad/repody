"""Sum and count the rows of an object-array field (a JSON list of objects).

Columns are the field's child names; a summed cell must be a number (declare the column
``number``), and the filter matches text case-insensitively.
"""

from __future__ import annotations

from typing import Any


def _rows(table: Any) -> list[dict[str, Any]]:
    return [row for row in table if isinstance(row, dict)] if isinstance(table, list) else []


def _matching(table: Any, filter_column: str, contains: str) -> list[dict[str, Any]]:
    needle = contains.strip().casefold()
    return [
        row
        for row in _rows(table)
        if not needle or needle in str(row.get(filter_column) or "").casefold()
    ]


def sum_rows(table: Any, amount_column: str, filter_column: str = "", contains: str = "") -> float:
    cells = (row.get(amount_column) for row in _matching(table, filter_column, contains))
    return sum(c for c in cells if isinstance(c, int | float) and not isinstance(c, bool))


def count_rows(table: Any, filter_column: str = "", contains: str = "") -> int:
    return len(_matching(table, filter_column, contains))
