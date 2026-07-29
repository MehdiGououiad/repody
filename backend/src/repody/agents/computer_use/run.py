"""Computer-use agent entry — SKIPPED until automation is implemented."""

from __future__ import annotations

from repody.agents.computer_use.contracts import ComputerUseInput, ComputerUseOutcome
from repody.runtime.contracts.agent import AgentId, AgentOutcome, AgentStatus
from repody.runtime.contracts.result import AppError, ErrorCode, Result


async def execute_computer_use(inp: ComputerUseInput) -> Result[AgentOutcome]:
    """SKIPPED shell until computer-use automation is implemented."""
    skipped = AppError(
        code=ErrorCode.SKIPPED, message="computer_use agent not implemented yet"
    )
    payload = ComputerUseOutcome(
        run_id=inp.run_id,
        summary="skipped: not implemented",
        errors=(skipped,),
    )
    return Result.ok(
        AgentOutcome(
            agent=AgentId.COMPUTER_USE,
            status=AgentStatus.SKIPPED,
            payload=payload,
            errors=(skipped,),
        )
    )
