"""Extracted values as rules see them: typed by the schema, never guessed from text.

NuExtract returns each field in its template type (a JSON number for ``number``, ISO 8601
text for ``date``, ``true``/``false`` for ``boolean``), so a value is read by the field's
declared type. A value that does not have that type counts as missing.
"""

from __future__ import annotations

from typing import Any

NUMBER_TYPES = frozenset({"number", "integer"})
TEMPORAL_TYPES = frozenset({"date", "date-time", "time"})  # ISO text orders correctly
ORDERED_TYPES = NUMBER_TYPES | TEMPORAL_TYPES
TABLE_TYPE = "object-array"


def field_key(name: str) -> str:
    """Canonical name of a field: ``Total Amount`` -> ``total_amount``, ``a.b`` -> ``a__b``."""
    return name.strip().lower().replace(" ", "_").replace(".", "__")


def typed(value: Any, field_type: str) -> Any:
    """An extracted value as its declared type, or None when it is missing or mistyped."""
    if value is None or value in ("", [], {}):
        return None
    if field_type in NUMBER_TYPES:
        return value if isinstance(value, int | float) and not isinstance(value, bool) else None
    if field_type == "boolean":
        return value if isinstance(value, bool) else None
    return value


def literal(text: str, field_type: str | None) -> Any:
    """What the user typed in a rule, read as the type of the field it is compared with.

    Raises ValueError when the text is not a value of that type.
    """
    text = text.strip()
    if field_type in NUMBER_TYPES:
        return float(text)
    if field_type == "boolean":
        if text.lower() not in ("true", "false"):
            raise ValueError(f"{text!r} is not true or false")
        return text.lower() == "true"
    return text
