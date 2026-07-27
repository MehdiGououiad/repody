"""Platform run orchestrator — staged recipe (one agent per Taskiq task)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.agents.computer_use.contracts import ComputerUseInput
from audit_workbench.agents.computer_use.run import execute_computer_use
from audit_workbench.agents.fraud.contracts import FraudInput
from audit_workbench.agents.fraud.run import execute_fraud
from audit_workbench.agents.idp.run import execute_idp_run
from audit_workbench.db.models import Run
from audit_workbench.platform.agent_metadata import (
    fraud_outcome_from_run,
    idp_outcome_from_run,
    record_agent_outcome,
)
from audit_workbench.platform.contracts.agent import AgentId, AgentOutcome
from audit_workbench.platform.contracts.result import AppError, ErrorCode, Result
from audit_workbench.settings import get_settings

log = structlog.get_logger()

DEFAULT_AGENT_ORDER: tuple[AgentId, ...] = (
    AgentId.IDP,
    AgentId.FRAUD,
    AgentId.COMPUTER_USE,
)


class AgentFlagSettings(Protocol):
    agent_idp_enabled: bool
    agent_fraud_enabled: bool
    agent_fraud_workers_ready: bool
    agent_computer_use_enabled: bool
    agent_computer_use_workers_ready: bool


@dataclass(frozen=True, slots=True)
class ResolvedRecipe:
    agents: tuple[AgentId, ...]


@dataclass(frozen=True, slots=True)
class PlatformStageResult:
    """Result of one agent stage — handoff when ``next_agent`` is set."""

    outcome: AgentOutcome
    next_agent: AgentId | None
    recipe: tuple[AgentId, ...]
    finalize_pending: bool = False


def _enabled_set(settings: AgentFlagSettings) -> set[AgentId]:
    """Agents that are both feature-flagged and worker-dispatchable."""
    enabled: set[AgentId] = set()
    if settings.agent_idp_enabled:
        enabled.add(AgentId.IDP)
    fraud_ready = settings.agent_fraud_workers_ready
    if settings.agent_fraud_enabled and fraud_ready:
        enabled.add(AgentId.FRAUD)
    elif settings.agent_fraud_enabled and not fraud_ready:
        log.warning(
            "agent_fraud_enabled_without_workers",
            event_domain="audit_run",
            hint="Set AUDIT_AGENT_FRAUD_WORKERS_READY=true when worker-fraud replicas > 0",
        )
    cu_ready = settings.agent_computer_use_workers_ready
    if settings.agent_computer_use_enabled and cu_ready:
        enabled.add(AgentId.COMPUTER_USE)
    elif settings.agent_computer_use_enabled and not cu_ready:
        log.warning(
            "agent_computer_use_enabled_without_workers",
            event_domain="audit_run",
            hint=(
                "Set AUDIT_AGENT_COMPUTER_USE_WORKERS_READY=true when "
                "worker-computer-use replicas > 0"
            ),
        )
    return enabled


def resolve_recipe(
    settings: AgentFlagSettings,
    requested: tuple[AgentId, ...] | None = None,
) -> Result[ResolvedRecipe]:
    """Intersect requested (or default) order with enable + workers-ready flags."""
    order = requested if requested is not None else DEFAULT_AGENT_ORDER
    enabled = _enabled_set(settings)
    agents = tuple(agent for agent in order if agent in enabled)

    if not agents:
        return Result.fail(
            AppError(code=ErrorCode.VALIDATION, message="no agents enabled for this run")
        )
    if AgentId.FRAUD in agents and AgentId.IDP not in agents:
        return Result.fail(
            AppError(code=ErrorCode.VALIDATION, message="fraud requires idp outcome")
        )
    return Result.ok(ResolvedRecipe(agents=agents))


def next_agent_after(
    recipe: tuple[AgentId, ...],
    current: AgentId,
) -> AgentId | None:
    """Return the next agent in the recipe after ``current``, or None if final."""
    try:
        idx = recipe.index(current)
    except ValueError:
        return None
    nxt = idx + 1
    if nxt >= len(recipe):
        return None
    return recipe[nxt]


async def execute_agent_stage(
    session: AsyncSession,
    run: Run,
    agent: AgentId,
    *,
    computer_use_goal: str = "",
    complete: bool,
) -> Result[AgentOutcome]:
    """Execute a single agent. IDP may defer complete when more stages follow."""
    if agent is AgentId.IDP:
        return await execute_idp_run(session, run, complete=complete)
    if agent is AgentId.FRAUD:
        return await execute_fraud(FraudInput(run_id=run.id, idp=idp_outcome_from_run(run)))
    if agent is AgentId.COMPUTER_USE:
        return await execute_computer_use(
            ComputerUseInput(
                run_id=run.id,
                goal=computer_use_goal,
                idp=idp_outcome_from_run(run),
                fraud=fraud_outcome_from_run(run),
            )
        )
    return Result.fail(
        AppError(code=ErrorCode.VALIDATION, message=f"unknown agent: {agent}")
    )


async def execute_platform_run(
    session: AsyncSession,
    run: Run,
    *,
    agent_stage: AgentId | None = None,
    requested: tuple[AgentId, ...] | None = None,
    computer_use_goal: str = "",
    settings: Any | None = None,
) -> PlatformStageResult:
    """Run **one** agent stage. Assumes IDP stage already claimed when applicable.

    Does not call ``complete_run`` for non-IDP finals — callers in services/run
    finalize via ``finalize_pending`` when ``result.finalize_pending`` is True.
    """
    cfg = settings if settings is not None else get_settings()
    recipe_r = resolve_recipe(cfg, requested)
    if not recipe_r.is_ok or recipe_r.value is None:
        err = recipe_r.error
        raise RuntimeError(err.message if err else "invalid agent recipe")

    recipe = recipe_r.value.agents
    agent = agent_stage if agent_stage is not None else recipe[0]
    if agent not in recipe:
        raise RuntimeError(f"agent {agent.value} not in recipe {[a.value for a in recipe]}")

    next_agent = next_agent_after(recipe, agent)
    will_complete = next_agent is None
    finalize_pending = will_complete and agent is not AgentId.IDP

    log.info(
        "platform_run_stage",
        event_domain="audit_run",
        run_id=run.id,
        agent=agent.value,
        next_agent=next_agent.value if next_agent else None,
        recipe=[a.value for a in recipe],
    )

    result = await execute_agent_stage(
        session,
        run,
        agent,
        computer_use_goal=computer_use_goal,
        complete=will_complete and agent is AgentId.IDP,
    )
    if not result.is_ok or result.value is None:
        err = result.error
        raise RuntimeError(err.message if err else f"agent {agent.value} failed")

    outcome = result.value
    # Reload run after IDP persist (may have committed).
    refreshed = await session.get(Run, run.id)
    if refreshed is None:
        raise RuntimeError(f"run vanished: {run.id}")
    record_agent_outcome(refreshed, outcome)
    await session.flush()
    await session.commit()

    log.info(
        "platform_agent_finished",
        event_domain="audit_run",
        run_id=run.id,
        agent=agent.value,
        status=outcome.status.value,
        next_agent=next_agent.value if next_agent else None,
        finalize_pending=finalize_pending,
    )
    return PlatformStageResult(
        outcome=outcome,
        next_agent=next_agent,
        recipe=recipe,
        finalize_pending=finalize_pending,
    )
