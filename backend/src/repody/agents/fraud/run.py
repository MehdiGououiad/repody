"""Fraud agent entry — SKIPPED until analysis is implemented."""

from __future__ import annotations

from repody.agents.fraud.contracts import FraudInput, FraudOutcome
from repody.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus
from repody.runtime.contracts.result import AppError, ErrorCode, Result


async def execute_fraud(inp: FraudInput) -> Result[AgentOutcome]:
    """SKIPPED shell until fraud analysis is implemented."""
    if inp.idp is None:
        return Result.fail(
            AppError(code=ErrorCode.VALIDATION, message="fraud requires idp outcome")
        )
    skipped = AppError(code=ErrorCode.SKIPPED, message="fraud agent not implemented yet")
    payload = FraudOutcome(
        run_id=inp.run_id,
        summary="skipped: not implemented",
        errors=(skipped,),
    )
    return Result.ok(
        AgentOutcome(
            agent=AgentId.FRAUD,
            status=AgentStatus.SKIPPED,
            payload=payload,
            errors=(skipped,),
        )
    )
