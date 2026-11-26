"""Sum and count the rows of an object-array field (a JSON list of objects).

Columns are the field's child names as written in the schema; a cell is found by that name,
or by its ``field_key`` when the model spelled the key differently. A summed cell must be a
number (declare the column ``number``); other cells (empty, "n/a") add nothing. The filter
matches text case-insensitively. A table that was not extracted is handled by the caller.
"""

from typing import Any

from repody.rules.values import is_number
from repody.schemas.catalog import field_key


def _rows(table: list[Any]) -> list[dict[str, Any]]:
    return [row for row in table if isinstance(row, dict)]


def _cell(row: dict[str, Any], column: str) -> Any:
    if column in row:
        return row[column]
    key = field_key(column)
    return next((value for name, value in row.items() if field_key(name) == key), None)


def _matching(table: list[Any], filter_column: str, contains: str) -> list[dict[str, Any]]:
    needle = contains.strip().casefold()
    if not needle or not filter_column:
        return _rows(table)
    return [
        row for row in _rows(table) if needle in str(_cell(row, filter_column) or "").casefold()
    ]


def sum_rows(table: list[Any], column: str, filter_column: str = "", contains: str = "") -> float:
    cells = (_cell(row, column) for row in _matching(table, filter_column, contains))
    return sum(cell for cell in cells if is_number(cell))


def count_rows(table: list[Any], filter_column: str = "", contains: str = "") -> int:
    return len(_matching(table, filter_column, contains))
