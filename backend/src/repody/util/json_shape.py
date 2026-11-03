"""Normalize JSON dict shapes for internal snake_case access."""

from __future__ import annotations

from typing import Any

from pydantic.alias_generators import to_snake


def normalize_keys_to_snake(obj: Any) -> Any:
    """Recursively convert camelCase dict keys to snake_case (Pydantic's ``to_snake``).

    If both ``fooBar`` and ``foo_bar`` are present, the snake_case value wins.
    """
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            snake = to_snake(str(key))
            if snake in out and key != snake:
                continue
            out[snake] = normalize_keys_to_snake(value)
        return out
    if isinstance(obj, list):
        return [normalize_keys_to_snake(item) for item in obj]
    return obj
