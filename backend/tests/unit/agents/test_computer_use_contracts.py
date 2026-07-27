"""Unit: Computer-use agent contracts and SKIPPED shell (ports-free)."""

from __future__ import annotations

import pytest

from audit_workbench.agents.computer_use import (
    ComputerUseInput,
    ComputerUseOutcome,
    execute_computer_use,
)
from audit_workbench.agents.fraud.contracts import FraudOutcome
from audit_workbench.agents.idp.contracts import ExtractionOutput, IdpOutcome, ValidationOutput
from audit_workbench.platform.contracts.agent import AgentId, AgentStatus
from audit_workbench.platform.contracts.result import ErrorCode


def _idp(run_id: str = "run-1") -> IdpOutcome:
    return IdpOutcome(
        run_id=run_id,
        workflow_id="wf-1",
        extraction=ExtractionOutput(by_document=()),
        validation=ValidationOutput(
            rule_results=(),
            overall_status="passed",
            summary_passed=0,
            summary_failed=0,
        ),
    )


@pytest.mark.asyncio
async def test_execute_computer_use_skipped_with_prior_outcomes():
    result = await execute_computer_use(
        ComputerUseInput(
            run_id="run-1",
            goal="open portal",
            idp=_idp(),
            fraud=FraudOutcome(run_id="run-1", summary="skipped"),
        )
    )
    assert result.is_ok
    outcome = result.unwrap()
    assert outcome.agent is AgentId.COMPUTER_USE
    assert outcome.status is AgentStatus.SKIPPED
    assert isinstance(outcome.payload, ComputerUseOutcome)
    assert outcome.payload.run_id == "run-1"
    assert outcome.errors
    assert outcome.errors[0].code is ErrorCode.SKIPPED


@pytest.mark.asyncio
async def test_execute_computer_use_allows_missing_priors():
    """Scaffold accepts empty priors; real CU may tighten this later."""
    result = await execute_computer_use(ComputerUseInput(run_id="run-1", goal=""))
    assert result.is_ok
    assert result.unwrap().status is AgentStatus.SKIPPED


def test_computer_use_outcome_defaults():
    payload = ComputerUseOutcome(run_id="run-1")
    assert payload.summary == ""
    assert payload.actions == ()
    assert payload.errors == ()
