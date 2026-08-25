"""Agent identity and outcome envelope."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from repody.runtime.contracts.result import AppError


class AgentId(StrEnum):
    IDP = "idp"


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
