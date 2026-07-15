"""Normalize JSON dict shapes for internal snake_case access."""

from __future__ import annotations

import re
from typing import Any

_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


def camel_to_snake(key: str) -> str:
    if "_" in key or not key:
        return key
    return _CAMEL_BOUNDARY.sub(r"\1_\2", key).lower()


def normalize_keys_to_snake(obj: Any) -> Any:
    """Recursively convert camelCase dict keys to snake_case.

    Already-snake keys are left unchanged. Lists are walked; scalars pass through.
    """
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            snake = camel_to_snake(str(key))
            # Prefer an existing snake_case value if both forms are present.
            if snake in out and key != snake:
                continue
            out[snake] = normalize_keys_to_snake(value)
        return out
    if isinstance(obj, list):
        return [normalize_keys_to_snake(item) for item in obj]
    return obj
