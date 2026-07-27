"""Unit tests for agent recipe flags and real SKIPPED agent shells — no mocked I/O."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from audit_workbench.agents.computer_use import ComputerUseInput, ComputerUseOutcome, execute_computer_use
from audit_workbench.agents.fraud import FraudInput, FraudOutcome, execute_fraud
from audit_workbench.agents.idp.contracts import ExtractionOutput, IdpOutcome, ValidationOutput
from audit_workbench.platform.contracts.agent import AgentId, AgentOutcome, AgentStatus
from audit_workbench.platform.contracts.context import AgentContext
from audit_workbench.platform.contracts.result import ErrorCode
from audit_workbench.platform.pools import agent_for_pool
from audit_workbench.platform.recipe import (
    DEFAULT_AGENT_ORDER,
    next_agent_after,
    resolve_recipe,
)


@dataclass
class _Flags:
    agent_idp_enabled: bool = True
    agent_fraud_enabled: bool = False
    agent_fraud_workers_ready: bool = False
    agent_computer_use_enabled: bool = False
    agent_computer_use_workers_ready: bool = False


def _idp_outcome(run_id: str = "run-1") -> IdpOutcome:
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


def test_default_recipe_idp_only():
    result = resolve_recipe(_Flags())
    assert result.is_ok
    assert result.value is not None
    assert result.value.agents == (AgentId.IDP,)


def test_recipe_includes_fraud_and_computer_use_when_enabled_and_workers_ready():
    result = resolve_recipe(
        _Flags(
            agent_fraud_enabled=True,
            agent_fraud_workers_ready=True,
            agent_computer_use_enabled=True,
            agent_computer_use_workers_ready=True,
        )
    )
    assert result.is_ok
    assert result.value is not None
    assert result.value.agents == DEFAULT_AGENT_ORDER


def test_recipe_omits_fraud_when_enabled_but_workers_not_ready():
    result = resolve_recipe(_Flags(agent_fraud_enabled=True, agent_fraud_workers_ready=False))
    assert result.is_ok
    assert result.value is not None
    assert result.value.agents == (AgentId.IDP,)


def test_recipe_omits_disabled_agents_from_requested():
    result = resolve_recipe(
        _Flags(agent_fraud_enabled=False),
        requested=(AgentId.IDP, AgentId.FRAUD, AgentId.COMPUTER_USE),
    )
    assert result.is_ok
    assert result.value is not None
    assert result.value.agents == (AgentId.IDP,)


def test_recipe_fail_closed_when_no_agents_enabled():
    result = resolve_recipe(_Flags(agent_idp_enabled=False))
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code is ErrorCode.VALIDATION
    assert "no agents enabled" in result.error.message


def test_recipe_fail_closed_when_fraud_without_idp():
    result = resolve_recipe(
        _Flags(
            agent_idp_enabled=False,
            agent_fraud_enabled=True,
            agent_fraud_workers_ready=True,
        ),
        requested=(AgentId.FRAUD,),
    )
    assert not result.is_ok
    assert result.error is not None
    assert "fraud requires idp" in result.error.message


def test_next_agent_after():
    recipe = DEFAULT_AGENT_ORDER
    assert next_agent_after(recipe, AgentId.IDP) is AgentId.FRAUD
    assert next_agent_after(recipe, AgentId.FRAUD) is AgentId.COMPUTER_USE
    assert next_agent_after(recipe, AgentId.COMPUTER_USE) is None
    assert next_agent_after((AgentId.IDP,), AgentId.IDP) is None


def test_agent_for_pool_mapping():
    assert agent_for_pool("extract") is AgentId.IDP
    assert agent_for_pool("fast") is AgentId.IDP
    assert agent_for_pool("fraud") is AgentId.FRAUD
    assert agent_for_pool("computer_use") is AgentId.COMPUTER_USE


def test_agent_context_chains_payloads():
    idp = _idp_outcome()
    fraud = FraudOutcome(run_id="run-1", summary="ok")
    ctx = AgentContext(run_id="run-1")
    ctx = ctx.with_outcome(
        AgentOutcome(agent=AgentId.IDP, status=AgentStatus.PASSED, payload=idp)
    )
    ctx = ctx.with_outcome(
        AgentOutcome(agent=AgentId.FRAUD, status=AgentStatus.SKIPPED, payload=fraud)
    )
    assert ctx.payload(AgentId.IDP) is idp
    assert ctx.payload(AgentId.FRAUD) is fraud
    assert ctx.payload(AgentId.COMPUTER_USE) is None


@pytest.mark.asyncio
async def test_execute_fraud_requires_idp_payload():
    result = await execute_fraud(FraudInput(run_id="run-1", idp=None))
    assert not result.is_ok
    assert result.error is not None
    assert "fraud requires idp" in result.error.message


@pytest.mark.asyncio
async def test_execute_fraud_skipped_shell_receives_idp():
    idp = _idp_outcome()
    result = await execute_fraud(FraudInput(run_id="run-1", idp=idp))
    assert result.is_ok
    assert result.value is not None
    assert result.value.agent is AgentId.FRAUD
    assert result.value.status is AgentStatus.SKIPPED
    assert isinstance(result.value.payload, FraudOutcome)
    assert result.value.payload.run_id == "run-1"


@pytest.mark.asyncio
async def test_execute_computer_use_skipped_shell():
    idp = _idp_outcome()
    fraud = FraudOutcome(run_id="run-1", summary="skipped")
    result = await execute_computer_use(
        ComputerUseInput(run_id="run-1", goal="open portal", idp=idp, fraud=fraud)
    )
    assert result.is_ok
    assert result.value is not None
    assert result.value.agent is AgentId.COMPUTER_USE
    assert result.value.status is AgentStatus.SKIPPED
    assert isinstance(result.value.payload, ComputerUseOutcome)
