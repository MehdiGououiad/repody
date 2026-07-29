"""Computer-use agent DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from audit_workbench.agents.fraud.contracts import FraudOutcome
from audit_workbench.agents.idp.contracts import IdpOutcome
from audit_workbench.runtime.contracts.result import AppError


@dataclass(frozen=True, slots=True)
class ComputerUseInput:
    run_id: str
    goal: str = ""
    idp: IdpOutcome | None = None
    fraud: FraudOutcome | None = None


@dataclass(frozen=True, slots=True)
class ComputerUseOutcome:
    run_id: str
    summary: str = ""
    actions: tuple[str, ...] = ()
    errors: tuple[AppError, ...] = ()
