"""Computer-use agent DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from repody.agents.fraud.contracts import FraudOutcome
from repody.agents.idp.contracts import IdpOutcome
from repody.runtime.contracts.result import AppError


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
