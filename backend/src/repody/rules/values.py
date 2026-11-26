"""Extracted values as rules see them: typed by the schema, never guessed from text.

NuExtract returns each field in its template type (a JSON number for ``number``, ISO 8601
text for ``date``, ``true``/``false`` for ``boolean``), so a value is read by the field's
declared type. A value that does not have that type counts as missing. Dates and times are
compared as dates and times (``2024-01-02T10:00:00+05:00`` is before ``…T06:00:00Z``), not as
text.
"""

import math
from collections.abc import Callable
from datetime import date, datetime, time
from typing import Any

from repody.schemas.catalog import NUMBER_TYPES, is_empty

_TEMPORAL: dict[str, Callable[[str], date | datetime | time]] = {
    "date": date.fromisoformat,
    "date-time": datetime.fromisoformat,
    "time": time.fromisoformat,
}


def is_number(value: Any) -> bool:
    """A real, finite number (``NaN`` and infinities compare false to everything)."""
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def typed(value: Any, field_type: str) -> Any:
    """An extracted value as its declared type, or None when it is missing or mistyped."""
    if is_empty(value):
        return None
    if field_type in NUMBER_TYPES:
        return value if is_number(value) else None
    if field_type == "boolean":
        return value if isinstance(value, bool) else None
    if parse := _TEMPORAL.get(field_type):
        try:
            return parse(value.strip()) if isinstance(value, str) else None
        except ValueError:
            return None
    return value


def literal(text: str, field_type: str | None) -> Any:
    """What the user typed in a rule, read as the type of the field it is compared with.

    Raises ValueError when the text is not a value of that type.
    """
    text = text.strip()
    if field_type in NUMBER_TYPES:
        number = float(text)
        if not math.isfinite(number):
            raise ValueError(f"{text!r} is not a number")
        return number
    if field_type == "boolean":
        if text.lower() not in ("true", "false"):
            raise ValueError(f"{text!r} is not true or false")
        return text.lower() == "true"
    if field_type and (parse := _TEMPORAL.get(field_type)):
        return parse(text)  # ValueError for text that is not ISO 8601
    return text
