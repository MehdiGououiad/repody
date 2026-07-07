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

    latency_rows = await session.execute(
        select(Run.workflow_id, Run.run_metadata).where(
            Run.workflow_id.in_(workflow_ids),
            Run.source == "api",
            Run.status == RunStatus.done.value,
            Run.run_metadata.is_not(None),
        )
    )
    latency_by_wf: dict[str, list[int]] = {}
    for wf_id, meta in latency_rows.all():
        if isinstance(meta, dict) and meta.get("durationMs"):
            latency_by_wf.setdefault(wf_id, []).append(int(meta["durationMs"]))

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
        durations = latency_by_wf.get(wf_id, [])
        avg_latency = int(sum(durations) / len(durations)) if durations else 0
        out[wf_id] = WorkflowApiStatsSchema(
            api_calls_today=today_map.get(wf_id, 0),
            api_calls_total=total,
            avg_latency_ms=avg_latency,
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
