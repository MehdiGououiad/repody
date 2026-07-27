"""Unit: Fraud agent contracts and SKIPPED shell (ports-free)."""

from __future__ import annotations

import pytest

from audit_workbench.agents.fraud import FraudInput, FraudOutcome, execute_fraud
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
async def test_execute_fraud_fail_closed_without_idp():
    result = await execute_fraud(FraudInput(run_id="run-1", idp=None))
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code is ErrorCode.VALIDATION
    assert "fraud requires idp" in result.error.message


@pytest.mark.asyncio
async def test_execute_fraud_skipped_envelope():
    result = await execute_fraud(FraudInput(run_id="run-1", idp=_idp()))
    assert result.is_ok
    outcome = result.unwrap()
    assert outcome.agent is AgentId.FRAUD
    assert outcome.status is AgentStatus.SKIPPED
    assert isinstance(outcome.payload, FraudOutcome)
    assert outcome.payload.run_id == "run-1"
    assert outcome.errors
    assert outcome.errors[0].code is ErrorCode.SKIPPED


def test_fraud_outcome_defaults():
    payload = FraudOutcome(run_id="run-1")
    assert payload.summary == ""
    assert payload.signals == ()
    assert payload.errors == ()
