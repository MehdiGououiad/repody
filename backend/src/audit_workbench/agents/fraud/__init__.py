"""Fraud detection agent (SKIPPED scaffold until implemented)."""

from audit_workbench.agents.fraud.contracts import FraudInput, FraudOutcome
from audit_workbench.agents.fraud.run import execute_fraud

__all__ = ["FraudInput", "FraudOutcome", "execute_fraud"]
