"""Fraud agent entry — SKIPPED until analysis is implemented."""

from __future__ import annotations

from audit_workbench.agents.fraud.contracts import FraudInput, FraudOutcome
from audit_workbench.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus
from audit_workbench.runtime.contracts.result import AppError, ErrorCode, Result


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
