"""Validate workflow rule bodies at authoring time."""

from __future__ import annotations

import re

from simpleeval import EvalWithCompoundTypes, simple_eval

_IDENTIFIER = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
_RESERVED = {
    "and",
    "or",
    "not",
    "True",
    "False",
    "None",
    "if",
    "else",
    "in",
    "is",
}


def _dummy_namespace_float(body: str) -> dict[str, float]:
    names: dict[str, float] = {}
    for token in _IDENTIFIER.findall(body):
        if token in _RESERVED:
            continue
        names.setdefault(token, 1.0)
    return names


def _dummy_namespace_str(body: str) -> dict[str, str]:
    names: dict[str, str] = {}
    for token in _IDENTIFIER.findall(body):
        if token in _RESERVED:
            continue
        names.setdefault(token, "2000-01-01")
    return names


def validate_logic_rule_body(body: str) -> str | None:
    expression = (body or "").strip()
    if not expression:
        return "Logic rule body is empty."
    evaluator = EvalWithCompoundTypes()
    last_type_error: Exception | None = None
    for namespace_factory in (_dummy_namespace_float, _dummy_namespace_str):
        try:
            simple_eval(
                expression,
                names=namespace_factory(expression),
                functions=evaluator.functions,
            )
            return None
        except TypeError as exc:
            last_type_error = exc
            continue
        except Exception as exc:
            return f"Invalid logic expression: {exc}"
    if last_type_error is not None:
        return f"Invalid logic expression: {last_type_error}"
    return "Invalid logic expression: incompatible operand types"


def validate_llm_rule_body(body: str, *, max_len: int = 4000) -> str | None:
    text = (body or "").strip()
    if not text:
        return "LLM rule body is empty."
    if len(text) > max_len:
        return f"LLM rule body exceeds {max_len} characters."
    return None


def validate_rule_dict(rule: dict) -> list[str]:
    kind = (rule.get("kind") or "logic").lower()
    label = (rule.get("name") or "").strip() or rule.get("id") or "Rule"
    body = rule.get("body") or ""
    if kind == "llm":
        err = validate_llm_rule_body(body)
    else:
        err = validate_logic_rule_body(body)
    return [f"{label}: {err}"] if err else []
