"""Unit tests for pool ↔ agent mapping."""

from __future__ import annotations

import pytest

from audit_workbench.platform.contracts.agent import AgentId
from audit_workbench.platform.pools import (
    agent_for_pool,
    parse_agent_stage,
    pool_for_agent,
)


def test_pool_for_agent_preserves_idp_capacity():
    assert pool_for_agent(AgentId.IDP, idp_pool="fast") == "fast"
    assert pool_for_agent(AgentId.IDP, idp_pool="extract") == "extract"
    assert pool_for_agent(AgentId.FRAUD) == "fraud"
    assert pool_for_agent(AgentId.COMPUTER_USE) == "computer_use"


def test_parse_agent_stage_defaults_idp():
    assert parse_agent_stage(None) is AgentId.IDP
    assert parse_agent_stage("fraud") is AgentId.FRAUD


def test_agent_for_pool_rejects_unknown():
    with pytest.raises(ValueError, match="unknown worker pool"):
        agent_for_pool("unknown")
