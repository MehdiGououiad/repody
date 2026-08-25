"""Unit tests for agent recipe resolution — IDP only."""

from __future__ import annotations

from dataclasses import dataclass

from repody.runtime.contracts.agent import AgentId
from repody.runtime.contracts.result import ErrorCode
from repody.runtime.pools import agent_for_pool
from repody.runtime.recipe import DEFAULT_AGENT_ORDER, resolve_recipe


@dataclass
class _Flags:
    agent_idp_enabled: bool = True


def test_default_recipe_idp_only():
    result = resolve_recipe(_Flags())
    assert result.is_ok
    assert result.value is not None
    assert result.value.agents == (AgentId.IDP,)
    assert DEFAULT_AGENT_ORDER == (AgentId.IDP,)


def test_recipe_fail_closed_when_no_agents_enabled():
    result = resolve_recipe(_Flags(agent_idp_enabled=False))
    assert not result.is_ok
    assert result.error is not None
    assert result.error.code is ErrorCode.VALIDATION
    assert "no agents enabled" in result.error.message


def test_agent_for_pool_mapping():
    assert agent_for_pool("extract") is AgentId.IDP
    assert agent_for_pool("fast") is AgentId.IDP
