"""Validate workflow rule bodies at authoring time."""

from __future__ import annotations

from simpleeval import EvalWithCompoundTypes, simple_eval

from repody.rules.expression import LOGIC_FUNCTIONS, field_identifiers
from repody.rules.types import rule_kind

# Sample values tried in order until the expression type-checks.
_SAMPLE_VALUES: tuple[object, ...] = (
    '[{"amount": 10.0, "category": "type-a"}]',
    1.0,
    "2000-01-01",
)


def _sample_namespace(body: str, value: object) -> dict[str, object]:
    return dict.fromkeys(field_identifiers(body), value)


def validate_logic_rule_body(body: str) -> str | None:
    expression = (body or "").strip()
    if not expression:
        return "Logic rule body is empty."
    evaluator = EvalWithCompoundTypes()
    functions = {**evaluator.functions, **LOGIC_FUNCTIONS}
    last_type_error: Exception | None = None
    for sample in _SAMPLE_VALUES:
        try:
            simple_eval(
                expression,
                names=_sample_namespace(expression, sample),
                functions=functions,
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
    kind = rule_kind(rule)
    label = (rule.get("name") or "").strip() or rule.get("id") or "Rule"
    body = rule.get("body") or ""
    err = validate_llm_rule_body(body) if kind == "llm" else validate_logic_rule_body(body)
    return [f"{label}: {err}"] if err else []
