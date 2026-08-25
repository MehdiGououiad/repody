"""Platform run orchestrator — one agent stage per Taskiq task (IDP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from repody.agents.idp.run import execute_idp_run
from repody.infra.db.models import Run
from repody.runtime.agent_metadata import record_agent_outcome
from repody.runtime.contracts.agent import AgentId, AgentOutcome
from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.settings import get_settings

log = structlog.get_logger()

DEFAULT_AGENT_ORDER: tuple[AgentId, ...] = (AgentId.IDP,)


class AgentFlagSettings(Protocol):
    agent_idp_enabled: bool


@dataclass(frozen=True, slots=True)
class ResolvedRecipe:
    agents: tuple[AgentId, ...]


@dataclass(frozen=True, slots=True)
class PlatformStageResult:
    """Result of one agent stage."""

    outcome: AgentOutcome
    recipe: tuple[AgentId, ...]


def _enabled_set(settings: AgentFlagSettings) -> set[AgentId]:
    enabled: set[AgentId] = set()
    if settings.agent_idp_enabled:
        enabled.add(AgentId.IDP)
    return enabled


def resolve_recipe(
    settings: AgentFlagSettings,
    requested: tuple[AgentId, ...] | None = None,
) -> Result[ResolvedRecipe]:
    """Intersect requested (or default) order with enable flags."""
    order = requested if requested is not None else DEFAULT_AGENT_ORDER
    enabled = _enabled_set(settings)
    agents = tuple(agent for agent in order if agent in enabled)

    if not agents:
        return Result.fail(
            AppError(code=ErrorCode.VALIDATION, message="no agents enabled for this run")
        )
    return Result.ok(ResolvedRecipe(agents=agents))


async def execute_agent_stage(
    session: AsyncSession,
    run: Run,
    agent: AgentId,
) -> Result[AgentOutcome]:
    """Execute a single agent stage. IDP always completes the platform run."""
    if agent is AgentId.IDP:
        return await execute_idp_run(session, run)
    return Result.fail(
        AppError(
            code=ErrorCode.VALIDATION,
            message=f"agent not implemented: {agent.value}",
        )
    )


async def execute_platform_run(
    session: AsyncSession,
    run: Run,
    *,
    agent_stage: AgentId | None = None,
    requested: tuple[AgentId, ...] | None = None,
    settings: Any | None = None,
) -> Result[PlatformStageResult]:
    """Run **one** agent stage. Assumes IDP stage already claimed when applicable.

    Returns ``Result`` at the recipe boundary (ADR-006); callers map failures
    once at the worker edge.
    """
    cfg = settings if settings is not None else get_settings()
    recipe_r = resolve_recipe(cfg, requested)
    if not recipe_r.is_ok or recipe_r.value is None:
        err = recipe_r.error
        return Result.fail(
            err or AppError(code=ErrorCode.VALIDATION, message="invalid agent recipe")
        )

    recipe = recipe_r.value.agents
    agent = agent_stage if agent_stage is not None else recipe[0]
    if agent not in recipe:
        return Result.fail(
            AppError(
                code=ErrorCode.VALIDATION,
                message=f"agent {agent.value} not in recipe {[a.value for a in recipe]}",
            )
        )

    log.info(
        "platform_run_stage",
        event_domain="audit_run",
        run_id=run.id,
        agent=agent.value,
        recipe=[a.value for a in recipe],
    )

    result = await execute_agent_stage(session, run, agent)
    if not result.is_ok or result.value is None:
        err = result.error
        return Result.fail(
            err
            or AppError(
                code=ErrorCode.VALIDATION,
                message=f"agent {agent.value} failed",
            )
        )

    outcome = result.value
    # Reload run after IDP persist (may have committed).
    refreshed = await session.get(Run, run.id)
    if refreshed is None:
        return Result.fail(AppError(code=ErrorCode.INFRA, message=f"run vanished: {run.id}"))
    record_agent_outcome(refreshed, outcome)
    await session.flush()
    await session.commit()

    log.info(
        "platform_agent_finished",
        event_domain="audit_run",
        run_id=run.id,
        agent=agent.value,
        status=outcome.status.value,
    )
    return Result.ok(PlatformStageResult(outcome=outcome, recipe=recipe))
