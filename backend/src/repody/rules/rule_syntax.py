"""Validate workflow rule bodies at authoring time."""

from __future__ import annotations

from repody.rules.expression import evaluate, referenced_names

# Field values are unknown when a rule is written: try each kind a field can hold
# (a table, a number, a date) until the expression type-checks.
_SAMPLE_VALUES: tuple[object, ...] = (
    '[{"amount": 10.0, "category": "type-a"}]',
    1.0,
    "2000-01-01",
)


def validate_logic_rule_body(body: str) -> str | None:
    """None when the expression parses and type-checks for some field kind, else the error."""
    expression = (body or "").strip()
    if not expression:
        return "Logic rule body is empty."
    try:
        names = referenced_names(expression)
    except SyntaxError as exc:
        return f"Invalid logic expression: {exc.msg}"
    error: Exception | None = None
    for sample in _SAMPLE_VALUES:
        try:
            evaluate(expression, dict.fromkeys(names, sample))
            return None
        except TypeError as exc:
            error = exc
        except Exception as exc:
            return f"Invalid logic expression: {exc}"
    return f"Invalid logic expression: {error}"
