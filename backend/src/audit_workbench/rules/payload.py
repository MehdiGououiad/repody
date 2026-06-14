"""Rule payload helpers at the run pipeline boundary."""

from __future__ import annotations

from typing import Any


def rule_kind(raw: dict[str, Any]) -> str:
    return str(raw.get("kind") or "logic").lower()


def llm_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [rule for rule in rules if rule_kind(rule) == "llm"]
