"""Fraud detection agent (SKIPPED scaffold until implemented)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from audit_workbench.agents.fraud.contracts import FraudInput, FraudOutcome

if TYPE_CHECKING:
    from audit_workbench.agents.fraud.run import execute_fraud as execute_fraud

__all__ = ["FraudInput", "FraudOutcome", "execute_fraud"]


def __getattr__(name: str) -> Any:
    if name == "execute_fraud":
        from audit_workbench.agents.fraud.run import execute_fraud

        return execute_fraud
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
