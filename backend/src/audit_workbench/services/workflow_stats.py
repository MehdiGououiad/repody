"""Real workflow and platform metrics from run data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import RuleResult, Run, RunStatus
from audit_workbench.schemas.workflow import (
    CallSeriesPointSchema,
    TopFailingRuleSchema,
    WorkflowApiStatsSchema,
)


async def batch_workflow_stats(
    session: AsyncSession,
    workflow_ids: list[str],
) -> dict[str, tuple[int, float, str | None]]:
    if not workflow_ids:
        return {}
    totals_q = await session.execute(
        select(Run.workflow_id, func.count(Run.id), func.max(Run.created_at))
        .where(Run.workflow_id.in_(workflow_ids), Run.status == RunStatus.done.value)
        .group_by(Run.workflow_id)
    )
    totals = {row[0]: (int(row[1]), row[2]) for row in totals_q.all()}

    passed_q = await session.execute(
        select(Run.workflow_id, func.count(Run.id))
        .where(
            Run.workflow_id.in_(workflow_ids),
            Run.status == RunStatus.done.value,
            Run.overall_status == "passed",
        )
        .group_by(Run.workflow_id)
    )
    passed_map = {row[0]: int(row[1]) for row in passed_q.all()}

    out: dict[str, tuple[int, float, str | None]] = {}
    for wf_id in workflow_ids:
        total, last_run = totals.get(wf_id, (0, None))
        passed = passed_map.get(wf_id, 0)
        rate = (passed / total) if total else 0.0
        last_str = last_run.strftime("%b %d, %H:%M") if last_run else None
        out[wf_id] = (total, rate, last_str)
    return out


async def workflow_stats(session: AsyncSession, workflow_id: str) -> tuple[int, float, str | None]:
    batch = await batch_workflow_stats(session, [workflow_id])
    return batch.get(workflow_id, (0, 0.0, None))


async def workflow_api_stats(
    session: AsyncSession,
    workflow_id: str,
) -> WorkflowApiStatsSchema | None:
    """Aggregate API run stats for a deployed workflow (no fabricated data)."""
    base = select(Run).where(Run.workflow_id == workflow_id, Run.source == "api")
    total_q = await session.execute(select(func.count()).select_from(base.subquery()))
    total = int(total_q.scalar() or 0)
    if total == 0:
        return WorkflowApiStatsSchema(
            api_calls_today=0,
            api_calls_total=0,
            avg_latency_ms=0,
            call_series=[],
            top_failing_rules=[],
        )

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_q = await session.execute(
        select(func.count()).select_from(
            select(Run)
            .where(
                Run.workflow_id == workflow_id,
                Run.source == "api",
                Run.created_at >= today_start,
            )
            .subquery()
        )
    )
    today = int(today_q.scalar() or 0)

    week_start = today_start - timedelta(days=6)
    series_q = await session.execute(
        select(func.date(Run.created_at), func.count(Run.id))
        .where(
            Run.workflow_id == workflow_id,
            Run.source == "api",
            Run.created_at >= week_start,
        )
        .group_by(func.date(Run.created_at))
        .order_by(func.date(Run.created_at))
    )
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    series_map = {str(row[0]): int(row[1]) for row in series_q.all()}
    call_series = [
        CallSeriesPointSchema(
            day=day_labels[i % 7],
            calls=series_map.get(str((week_start + timedelta(days=i)).date()), 0),
        )
        for i in range(7)
    ]

    latency_rows = await session.execute(
        select(Run.run_metadata).where(
            Run.workflow_id == workflow_id,
            Run.source == "api",
            Run.status == RunStatus.done.value,
            Run.run_metadata.is_not(None),
        )
    )
    durations = [
        int(meta.get("durationMs") or 0)
        for meta in latency_rows.scalars()
        if isinstance(meta, dict) and meta.get("durationMs")
    ]
    avg_latency = int(sum(durations) / len(durations)) if durations else 0

    failing_q = await session.execute(
        select(RuleResult.name, RuleResult.severity, func.count(RuleResult.id))
        .join(Run, Run.id == RuleResult.run_id)
        .where(
            Run.workflow_id == workflow_id,
            Run.source == "api",
            RuleResult.status.in_(("failed", "error")),
        )
        .group_by(RuleResult.name, RuleResult.severity)
        .order_by(func.count(RuleResult.id).desc())
        .limit(5)
    )
    top_failing = [
        TopFailingRuleSchema(name=row[0], count=int(row[2]), severity=row[1] or "reject")
        for row in failing_q.all()
    ]

    return WorkflowApiStatsSchema(
        api_calls_today=today,
        api_calls_total=total,
        avg_latency_ms=avg_latency,
        call_series=call_series,
        top_failing_rules=top_failing,
    )
