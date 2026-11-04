"""Workflow use cases: list, read, create, save, archive, deploy, and run statistics."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.errors import AppError
from repody.extraction.fields import leaves
from repody.infra.auth import api_key_hint, hash_api_key, new_api_key
from repody.infra.models import RuleResult, Run, Workflow, new_id
from repody.rules.evaluate import condition_issue, describe, rule_issues
from repody.rules.values import field_key
from repody.schemas.workflow import (
    ApiStats,
    CallsPerDay,
    CreateWorkflow,
    DocumentDef,
    FailingRule,
    RuleCheck,
    WorkflowDefinition,
    WorkflowIn,
    WorkflowOut,
)


async def _run_stats(
    session: AsyncSession, workflow_ids: list[str]
) -> dict[str, tuple[int, float, datetime | None]]:
    """``(total runs, share of finished runs that passed, last run)`` per workflow."""
    rows = await session.execute(
        select(
            Run.workflow_id,
            func.count(),
            func.count().filter(Run.outcome == "passed"),
            func.count().filter(Run.status == "done"),
            func.max(Run.created_at),
        )
        .where(Run.workflow_id.in_(workflow_ids))
        .group_by(Run.workflow_id)
    )
    return {
        wf_id: (total, passed / done if done else 0.0, last)
        for wf_id, total, passed, done, last in rows.tuples()
    }


async def _api_stats(session: AsyncSession, workflow_id: str) -> ApiStats:
    api_runs = (Run.workflow_id == workflow_id) & (Run.source == "api")
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    week = today - timedelta(days=6)
    total, today_count, avg_ms = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(Run.created_at >= today),
                func.avg(func.extract("epoch", Run.finished_at - Run.started_at) * 1000),
            ).where(api_runs)
        )
    ).one()
    per_day = dict(
        (
            await session.execute(
                select(func.date(Run.created_at), func.count())
                .where(api_runs, Run.created_at >= week)
                .group_by(func.date(Run.created_at))
            )
        )
        .tuples()
        .all()
    )
    failing = await session.execute(
        select(RuleResult.name, RuleResult.severity, func.count())
        .join(Run, Run.id == RuleResult.run_id)
        .where(api_runs, RuleResult.status == "failed")
        .group_by(RuleResult.name, RuleResult.severity)
        .order_by(func.count().desc())
        .limit(5)
    )
    days = [(week + timedelta(days=i)).date() for i in range(7)]
    return ApiStats(
        api_calls_today=today_count,
        api_calls_total=total,
        avg_latency_ms=int(avg_ms or 0),
        call_series=[CallsPerDay(day=d.strftime("%a"), calls=per_day.get(d, 0)) for d in days],
        top_failing_rules=[
            FailingRule(name=name, severity=severity, count=count)
            for name, severity, count in failing.tuples()
        ],
    )


def _out(
    wf: Workflow,
    stats: tuple[int, float, datetime | None] = (0, 0.0, None),
    *,
    with_definition: bool = True,
    api_stats: ApiStats | None = None,
    api_key: str | None = None,
) -> WorkflowOut:
    definition = WorkflowDefinition.model_validate(wf.definition if with_definition else {})
    return WorkflowOut(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        status=wf.status,  # type: ignore[arg-type]
        owner=wf.owner,
        documents=definition.documents,
        rules=definition.rules,
        deployed_at=wf.deployed_at,
        api_key=api_key,
        api_key_hint=wf.api_key_hint,
        total_runs=stats[0],
        success_rate=stats[1],
        last_run=stats[2],
        api_stats=api_stats,
    )


async def load(session: AsyncSession, workflow_id: str) -> Workflow:
    wf = await session.get(Workflow, workflow_id)
    if wf is None or wf.status == "archived":
        raise AppError(404, "Workflow not found.")
    return wf


async def list_workflows(session: AsyncSession) -> list[WorkflowOut]:
    """Cards for the workflow list: no definition, no API stats."""
    workflows = (
        await session.scalars(
            select(Workflow)
            .where(Workflow.status != "archived")
            .order_by(Workflow.updated_at.desc())
        )
    ).all()
    stats = await _run_stats(session, [wf.id for wf in workflows])
    return [_out(wf, stats.get(wf.id, (0, 0.0, None)), with_definition=False) for wf in workflows]


async def get_workflow(
    session: AsyncSession, workflow_id: str, *, api_key: str | None = None
) -> WorkflowOut:
    wf = await load(session, workflow_id)
    stats = (await _run_stats(session, [wf.id])).get(wf.id, (0, 0.0, None))
    api_stats = await _api_stats(session, wf.id) if wf.deployed_at else None
    return _out(wf, stats, api_stats=api_stats, api_key=api_key)


async def create_workflow(session: AsyncSession, body: CreateWorkflow) -> WorkflowOut:
    definition = WorkflowDefinition(documents=[DocumentDef(id=new_id("doc"))])
    wf = Workflow(
        id=new_id("wf"),
        name=body.name,
        description=body.description,
        owner=body.owner,
        definition=definition.model_dump(),
    )
    session.add(wf)
    await session.flush()
    return _out(wf)


def field_types(definition: WorkflowDefinition) -> dict[str, str]:
    """Template type of every field a rule can name: ``field`` and ``document type.field``."""
    types: dict[str, str] = {}
    for doc in definition.documents:
        for key, field, _value in leaves(doc.schema_fields):
            types.setdefault(field_key(key), field.template_type)
            types[field_key(f"{doc.document_type}.{key}")] = field.template_type
    return types


def rule_check_issues(definition: WorkflowDefinition) -> list[str]:
    types = field_types(definition)
    return [issue for rule in definition.rules for issue in rule_issues(rule, types)]


async def save_workflow(session: AsyncSession, workflow_id: str, body: WorkflowIn) -> WorkflowOut:
    """Create or replace the workflow (the builder saves the whole definition)."""
    if issues := rule_check_issues(body):
        raise AppError(422, "; ".join(issues))
    wf = await session.get(Workflow, workflow_id)
    if wf is None:
        wf = Workflow(id=workflow_id)
        session.add(wf)
    wf.name, wf.description, wf.status, wf.owner = (
        body.name,
        body.description,
        body.status,
        body.owner,
    )
    wf.definition = body.model_dump(include={"documents", "rules"})
    await session.flush()
    return await get_workflow(session, workflow_id)


async def archive_workflows(session: AsyncSession, workflow_ids: list[str]) -> None:
    for wf in await session.scalars(select(Workflow).where(Workflow.id.in_(workflow_ids))):
        wf.status = "archived"


async def deploy_workflow(session: AsyncSession, workflow_id: str) -> WorkflowOut:
    """Activate the workflow with a new API key, returned once."""
    wf = await load(session, workflow_id)
    key = new_api_key()
    wf.deployed_at, wf.status = datetime.now(UTC), "active"
    wf.api_key_hash, wf.api_key_hint = hash_api_key(key), api_key_hint(key)
    await session.flush()
    return await get_workflow(session, workflow_id, api_key=key)


def check_rules(definition: WorkflowDefinition) -> list[RuleCheck]:
    """Builder feedback: issues and the readable form of every condition."""
    types = field_types(definition)
    return [
        RuleCheck(
            rule_id=rule.id,
            issues=rule_issues(rule, types),
            checks=["" if condition_issue(c) else describe(c) for c in rule.conditions],
        )
        for rule in definition.rules
    ]
