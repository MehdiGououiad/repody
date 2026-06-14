from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import lru_cache

from audit_workbench.rules.evaluators.base import RuleEvaluator
from audit_workbench.rules.evaluators.llm import LlmRuleEvaluator
from audit_workbench.rules.evaluators.logic import LogicRuleEvaluator


@lru_cache
def get_rule_evaluator(kind: str) -> RuleEvaluator:
    normalized = (kind or "logic").lower()
    if normalized == "llm":
        return LlmRuleEvaluator()
    return LogicRuleEvaluator()
