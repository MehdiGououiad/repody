"""Map Taskiq worker pools ↔ agent stages.

extract/fast are IDP capacity classes (document vs logic-only).
fraud / computer_use are dedicated agent pools for independent scaling.
"""

from __future__ import annotations

from audit_workbench.runtime.contracts.agent import AgentId

POOL_EXTRACT = "extract"
POOL_FAST = "fast"
POOL_FRAUD = "fraud"
POOL_COMPUTER_USE = "computer_use"

IDP_POOLS: frozenset[str] = frozenset({POOL_EXTRACT, POOL_FAST})
ALL_AGENT_POOLS: frozenset[str] = frozenset(
    {POOL_EXTRACT, POOL_FAST, POOL_FRAUD, POOL_COMPUTER_USE}
)


def agent_for_pool(pool: str) -> AgentId:
    """Resolve which agent a worker pool executes."""
    normalized = (pool or "").strip().lower()
    if normalized in IDP_POOLS:
        return AgentId.IDP
    if normalized == POOL_FRAUD:
        return AgentId.FRAUD
    if normalized == POOL_COMPUTER_USE:
        return AgentId.COMPUTER_USE
    raise ValueError(f"unknown worker pool: {pool!r}")


def pool_for_agent(agent: AgentId, *, idp_pool: str = POOL_EXTRACT) -> str:
    """Queue suffix for the next agent stage.

    IDP keeps the run's existing extract/fast classification via ``idp_pool``.
    """
    if agent is AgentId.IDP:
        pool = (idp_pool or POOL_EXTRACT).strip().lower()
        if pool not in IDP_POOLS:
            return POOL_EXTRACT
        return pool
    if agent is AgentId.FRAUD:
        return POOL_FRAUD
    if agent is AgentId.COMPUTER_USE:
        return POOL_COMPUTER_USE
    raise ValueError(f"unknown agent: {agent}")


def parse_agent_stage(value: str | None) -> AgentId:
    """Parse task ``agent_stage`` label; default idp."""
    raw = (value or AgentId.IDP.value).strip().lower()
    try:
        return AgentId(raw)
    except ValueError as exc:
        raise ValueError(f"unknown agent_stage: {value!r}") from exc
