"""Fraud agent DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from audit_workbench.agents.idp.contracts import IdpOutcome
from audit_workbench.runtime.contracts.result import AppError


@dataclass(frozen=True, slots=True)
class FraudInput:
    run_id: str
    idp: IdpOutcome | None = None


@dataclass(frozen=True, slots=True)
class FraudOutcome:
    run_id: str
    summary: str = ""
    signals: tuple[str, ...] = ()
    errors: tuple[AppError, ...] = ()
