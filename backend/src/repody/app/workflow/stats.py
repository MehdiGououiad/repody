"""Real workflow and platform metrics from run data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.db.models import RuleResult, Run, RunStatus
from repody.schemas.workflow import (
    CallSeriesPointSchema,
    TopFailingRuleSchema,
    WorkflowApiStatsSchema,
)


async def batch_workflow_stats(
    session: AsyncSession,
    workflow_ids: list[str],
) -> dict[str, tuple[int, float, str | None]]:
    """One aggregate query: total done runs, passed count, last run time per workflow."""
    if not workflow_ids:
        return {}
    rows = await session.execute(
        select(
            Run.workflow_id,
            func.count(Run.id),
            func.count().filter(Run.overall_status == "passed"),
            func.max(Run.created_at),
        )
        .where(Run.workflow_id.in_(workflow_ids), Run.status == RunStatus.done.value)
        .group_by(Run.workflow_id)
    )
    out: dict[str, tuple[int, float, str | None]] = {}
    for wf_id, total, passed, last_run in rows.all():
        total_i = int(total or 0)
        passed_i = int(passed or 0)
        rate = (passed_i / total_i) if total_i else 0.0
        last_str = last_run.strftime("%b %d, %H:%M") if last_run else None
        out[wf_id] = (total_i, rate, last_str)
    for wf_id in workflow_ids:
        out.setdefault(wf_id, (0, 0.0, None))
    return out


async def workflow_stats(session: AsyncSession, workflow_id: str) -> tuple[int, float, str | None]:
    batch = await batch_workflow_stats(session, [workflow_id])
    return batch.get(workflow_id, (0, 0.0, None))


async def batch_workflow_api_stats(
    session: AsyncSession,
    workflow_ids: list[str],
) -> dict[str, WorkflowApiStatsSchema]:
    if not workflow_ids:
        return {}

    empty = WorkflowApiStatsSchema(
        api_calls_today=0,
        api_calls_total=0,
        avg_latency_ms=0,
        call_series=[],
        top_failing_rules=[],
    )

    totals_q = await session.execute(
        select(Run.workflow_id, func.count(Run.id))
        .where(Run.workflow_id.in_(workflow_ids), Run.source == "api")
        .group_by(Run.workflow_id)
    )
    totals = {row[0]: int(row[1]) for row in totals_q.all()}
    if not totals:
        return dict.fromkeys(workflow_ids, empty)

    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_q = await session.execute(
        select(Run.workflow_id, func.count(Run.id))
        .where(
            Run.workflow_id.in_(workflow_ids),
            Run.source == "api",
            Run.created_at >= today_start,
        )
        .group_by(Run.workflow_id)
    )
    today_map = {row[0]: int(row[1]) for row in today_q.all()}

    week_start = today_start - timedelta(days=6)
    series_q = await session.execute(
        select(Run.workflow_id, func.date(Run.created_at), func.count(Run.id))
        .where(
            Run.workflow_id.in_(workflow_ids),
            Run.source == "api",
            Run.created_at >= week_start,
        )
        .group_by(Run.workflow_id, func.date(Run.created_at))
    )
    series_by_wf: dict[str, dict[str, int]] = {}
    for wf_id, day, count in series_q.all():
        series_by_wf.setdefault(wf_id, {})[str(day)] = int(count)

    latency_q = await session.execute(
        select(
            Run.workflow_id,
            func.avg(func.nullif(Run.run_metadata["durationMs"].as_float(), 0.0)),
        )
        .where(
            Run.workflow_id.in_(workflow_ids),
            Run.source == "api",
            Run.status == RunStatus.done.value,
            Run.run_metadata.is_not(None),
        )
        .group_by(Run.workflow_id)
    )
    latency_by_wf = {
        wf_id: int(avg_ms) if avg_ms is not None else 0 for wf_id, avg_ms in latency_q.all()
    }

    failing_q = await session.execute(
        select(
            Run.workflow_id,
            RuleResult.name,
            RuleResult.severity,
            func.count(RuleResult.id),
        )
        .join(Run, Run.id == RuleResult.run_id)
        .where(
            Run.workflow_id.in_(workflow_ids),
            Run.source == "api",
            RuleResult.status.in_(("failed", "error")),
        )
        .group_by(Run.workflow_id, RuleResult.name, RuleResult.severity)
        .order_by(Run.workflow_id, func.count(RuleResult.id).desc())
    )
    failing_by_wf: dict[str, list[TopFailingRuleSchema]] = {}
    for wf_id, name, severity, count in failing_q.all():
        rows = failing_by_wf.setdefault(wf_id, [])
        if len(rows) < 5:
            rows.append(
                TopFailingRuleSchema(name=name, count=int(count), severity=severity or "reject")
            )

    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    out: dict[str, WorkflowApiStatsSchema] = {}
    for wf_id in workflow_ids:
        total = totals.get(wf_id, 0)
        if total == 0:
            out[wf_id] = empty
            continue
        series_map = series_by_wf.get(wf_id, {})
        call_series = [
            CallSeriesPointSchema(
                day=day_labels[i % 7],
                calls=series_map.get(str((week_start + timedelta(days=i)).date()), 0),
            )
            for i in range(7)
        ]
        out[wf_id] = WorkflowApiStatsSchema(
            api_calls_today=today_map.get(wf_id, 0),
            api_calls_total=total,
            avg_latency_ms=latency_by_wf.get(wf_id, 0),
            call_series=call_series,
            top_failing_rules=failing_by_wf.get(wf_id, []),
        )
    return out


async def workflow_api_stats(
    session: AsyncSession,
    workflow_id: str,
) -> WorkflowApiStatsSchema | None:
    """Aggregate API run stats for a deployed workflow (no fabricated data)."""
    batch = await batch_workflow_api_stats(session, [workflow_id])
    return batch.get(workflow_id)
