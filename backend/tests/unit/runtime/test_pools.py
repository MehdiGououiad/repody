"""Unit tests for pool ↔ agent mapping."""

from __future__ import annotations

import pytest

from repody.runtime.contracts.agent import AgentId
from repody.runtime.pools import (
    agent_for_pool,
    parse_agent_stage,
    pool_for_agent,
)


def test_pool_for_agent_preserves_idp_capacity():
    assert pool_for_agent(AgentId.IDP, idp_pool="fast") == "fast"
    assert pool_for_agent(AgentId.IDP, idp_pool="extract") == "extract"


def test_pool_for_agent_falls_back_to_extract_for_unknown_capacity():
    assert pool_for_agent(AgentId.IDP, idp_pool="nonsense") == "extract"


def test_parse_agent_stage_defaults_idp():
    assert parse_agent_stage(None) is AgentId.IDP
    assert parse_agent_stage("idp") is AgentId.IDP


def test_parse_agent_stage_rejects_unknown():
    with pytest.raises(ValueError, match="unknown agent_stage"):
        parse_agent_stage("fraud")


def test_agent_for_pool_rejects_unknown():
    with pytest.raises(ValueError, match="unknown worker pool"):
        agent_for_pool("unknown")
