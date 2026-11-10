"""Workflow use cases: list, read, create, save, archive, deploy, and run statistics."""

from collections import Counter
from datetime import UTC, datetime
from typing import NamedTuple

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.errors import AppError
from repody.app.stats import daily_counts, last_days, midnight, pass_rate, today
from repody.extraction.fields import leaves
from repody.infra.auth import api_key_hint, hash_api_key, new_api_key
from repody.infra.models import RuleResult, Run, Workflow, new_id
from repody.rules.evaluate import SchemaTypes, condition_issue, describe, rule_issues
from repody.schemas.catalog import TABLE_TYPE, field_key
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


class RunStats(NamedTuple):
    total: int = 0
    success_rate: float = 0.0  # share of finished runs that passed
    last_run: datetime | None = None


async def _run_stats(session: AsyncSession, workflow_ids: list[str]) -> dict[str, RunStats]:
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
        wf_id: RunStats(total, pass_rate(passed, done), last)
        for wf_id, total, passed, done, last in rows
    }


async def _api_stats(session: AsyncSession, workflow_id: str) -> ApiStats:
    api_runs = (Run.workflow_id == workflow_id) & (Run.source == "api")
    week = last_days(7)
    total, today_count, avg_ms = (
        await session.execute(
            select(
                func.count(),
                func.count().filter(Run.created_at >= midnight(today())),
                func.avg(func.extract("epoch", Run.finished_at - Run.started_at) * 1000),
            ).where(api_runs)
        )
    ).one()
    per_day = await daily_counts(session, week[0], api_runs)
    failing = await session.execute(
        select(RuleResult.name, RuleResult.severity, func.count())
        .join(Run, Run.id == RuleResult.run_id)
        .where(api_runs, RuleResult.status == "failed")
        .group_by(RuleResult.name, RuleResult.severity)
        .order_by(func.count().desc())
        .limit(5)
    )
    return ApiStats(
        api_calls_today=today_count,
        api_calls_total=total,
        avg_latency_ms=int(avg_ms or 0),
        call_series=[
            CallsPerDay(day=d, calls=per_day[d].runs if d in per_day else 0) for d in week
        ],
        top_failing_rules=[
            FailingRule(name=name, severity=severity, count=count)
            for name, severity, count in failing
        ],
    )


def _out(
    wf: Workflow,
    definition: WorkflowDefinition,
    stats: RunStats,
    *,
    api_stats: ApiStats | None = None,
    api_key: str | None = None,
) -> WorkflowOut:
    return WorkflowOut(
        id=wf.id,
        name=wf.name,
        description=wf.description,
        status="active" if wf.status == "active" else "draft",  # archived ones are never returned
        owner=wf.owner,
        documents=definition.documents,
        rules=definition.rules,
        deployed_at=wf.deployed_at,
        api_key=api_key,
        api_key_hint=wf.api_key_hint,
        total_runs=stats.total,
        success_rate=stats.success_rate,
        last_run=stats.last_run,
        api_stats=api_stats,
    )


async def find(session: AsyncSession, workflow_id: str) -> Workflow | None:
    """The workflow, or None when it does not exist or is archived."""
    wf = await session.get(Workflow, workflow_id)
    return None if wf is None or wf.status == "archived" else wf


async def load(session: AsyncSession, workflow_id: str) -> Workflow:
    if (wf := await find(session, workflow_id)) is None:
        raise AppError(404, "Workflow not found.")
    return wf


async def list_workflows(session: AsyncSession, *, limit: int | None = None) -> list[WorkflowOut]:
    """Cards for the workflow list, most recently edited first: no definition, no API stats."""
    workflows = (
        await session.scalars(
            select(Workflow)
            .where(Workflow.status != "archived")
            .order_by(Workflow.updated_at.desc())
            .limit(limit)
        )
    ).all()
    stats = await _run_stats(session, [wf.id for wf in workflows])
    empty = WorkflowDefinition()
    return [_out(wf, empty, stats.get(wf.id, RunStats())) for wf in workflows]


async def get_workflow(
    session: AsyncSession, workflow_id: str, *, api_key: str | None = None
) -> WorkflowOut:
    wf = await load(session, workflow_id)
    stats = (await _run_stats(session, [wf.id])).get(wf.id, RunStats())
    api_stats = await _api_stats(session, wf.id) if wf.deployed_at else None
    definition = WorkflowDefinition.model_validate(wf.definition)
    return _out(wf, definition, stats, api_stats=api_stats, api_key=api_key)


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
    return _out(wf, definition, RunStats())


def schema_types(definition: WorkflowDefinition) -> SchemaTypes:
    """Every field a rule can name (``field`` and ``document type.field``) with its type,
    and the columns of every object-array field."""
    fields: dict[str, str] = {}
    columns: dict[str, dict[str, str]] = {}
    documents_with: Counter[str] = Counter()  # bare name -> how many documents have it
    for doc in definition.documents:
        for key, field, _value in leaves(doc.schema_fields):
            documents_with[field_key(key)] += 1
            for name in (field_key(key), field_key(f"{doc.document_type}.{key}")):
                fields.setdefault(name, field.template_type)
                if field.template_type == TABLE_TYPE:
                    columns.setdefault(
                        name, {field_key(c.name): c.template_type for c in field.children}
                    )
    # A bare name in several documents is ambiguous: rules must name the document.
    for name, count in documents_with.items():
        if count > 1:
            fields.pop(name, None)
            columns.pop(name, None)
    return SchemaTypes(fields=fields, columns=columns)


async def save_workflow(session: AsyncSession, workflow_id: str, body: WorkflowIn) -> WorkflowOut:
    """Create or replace the workflow's definition (the builder saves all of it); its status
    does not change."""
    types = schema_types(body)
    if issues := [issue for rule in body.rules for issue in rule_issues(rule, types)]:
        raise AppError(422, "; ".join(issues))
    # Create the draft if it is new: one statement, so two first saves cannot both insert it.
    await session.execute(
        insert(Workflow)
        .values(id=workflow_id, status="draft", definition={})
        .on_conflict_do_nothing(index_elements=[Workflow.id])
    )
    wf = await session.get_one(Workflow, workflow_id, with_for_update=True)
    if wf.status == "archived":
        raise AppError(404, "Workflow not found.")
    wf.name, wf.description, wf.owner = body.name, body.description, body.owner
    wf.definition = body.model_dump(include={"documents", "rules"})
    await session.flush()
    return await get_workflow(session, workflow_id)


async def archive_workflows(session: AsyncSession, workflow_ids: list[str]) -> None:
    """Archive the workflows (final); their API keys stop working."""
    await session.execute(
        update(Workflow).where(Workflow.id.in_(workflow_ids)).values(status="archived")
    )


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
    types = schema_types(definition)
    return [
        RuleCheck(
            rule_id=rule.id,
            issues=rule_issues(rule, types),
            checks=["" if condition_issue(c) else describe(c) for c in rule.conditions],
        )
        for rule in definition.rules
    ]
