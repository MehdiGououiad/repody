from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from audit_workbench.rules.types import RuleEvalResult


class RuleEvaluator(ABC):
    kind: str

    @abstractmethod
    async def evaluate_rules(
        self,
        rules: list[dict],
        field_values: dict[str, str],
        *,
        on_rule_start: Callable[[dict], Awaitable[None]] | None = None,
        llm_model: str | None = None,
    ) -> list[RuleEvalResult]: ...
