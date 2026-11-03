"""Vocabulary shared by logic-rule authoring checks and evaluation."""

from __future__ import annotations

import ast
from typing import Any

from simpleeval import EvalWithCompoundTypes

from repody.rules.table_aggregates import count_rows_where, sum_rows, sum_rows_where

LOGIC_FUNCTIONS: dict[str, Any] = {
    "sum_rows": sum_rows,
    "sum_rows_where": sum_rows_where,
    "count_rows_where": count_rows_where,
}


def field_key(name: str) -> str:
    """Canonical rule name of a field: lower snake case, ``doc.field`` written ``doc__field``.

    ``Total Amount`` -> ``total_amount``; ``invoice.total`` -> ``invoice__total``.
    """
    return name.strip().lower().replace(" ", "_").replace(".", "__")


def referenced_names(expression: str) -> list[str]:
    """Variable names an expression reads, in order (function names excluded).

    Raises SyntaxError for an expression Python cannot parse.
    """
    tree = ast.parse(expression.strip(), mode="eval")
    # Function names and comprehension variables are not fields.
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    bound = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
    }
    names = sorted(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Name) and node.id not in called | bound
        ),
        key=lambda node: (node.lineno, node.col_offset),
    )
    return list(dict.fromkeys(node.id for node in names))


def evaluate(expression: str, names: dict[str, Any]) -> Any:
    """Evaluate with simpleeval: compound types allowed, rule functions available."""
    evaluator = EvalWithCompoundTypes(names=names)
    evaluator.functions = {**evaluator.functions, **LOGIC_FUNCTIONS}
    return evaluator.eval(expression)
