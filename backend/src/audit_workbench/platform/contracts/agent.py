"""Agent identity and outcome envelope for IDP / Fraud / Computer Use."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from audit_workbench.platform.contracts.result import AppError


class AgentId(StrEnum):
    IDP = "idp"
    FRAUD = "fraud"
    COMPUTER_USE = "computer_use"


class AgentStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class AgentOutcome:
    """Common envelope — downstream agents consume prior payloads without ORM coupling."""

    agent: AgentId
    status: AgentStatus
    payload: Any
    errors: tuple[AppError, ...] = ()
