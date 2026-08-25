"""Map Taskiq worker pools ↔ agent stages.

extract/fast are IDP capacity classes (document-model work vs logic-only).
"""

from __future__ import annotations

from repody.runtime.contracts.agent import AgentId

POOL_EXTRACT = "extract"
POOL_FAST = "fast"

IDP_POOLS: frozenset[str] = frozenset({POOL_EXTRACT, POOL_FAST})
ALL_AGENT_POOLS: frozenset[str] = IDP_POOLS


def agent_for_pool(pool: str) -> AgentId:
    """Resolve which agent a worker pool executes."""
    normalized = (pool or "").strip().lower()
    if normalized in IDP_POOLS:
        return AgentId.IDP
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
    raise ValueError(f"unknown agent: {agent}")


def parse_agent_stage(value: str | None) -> AgentId:
    """Parse task ``agent_stage`` label; default idp."""
    raw = (value or AgentId.IDP.value).strip().lower()
    try:
        return AgentId(raw)
    except ValueError as exc:
        raise ValueError(f"unknown agent_stage: {value!r}") from exc
