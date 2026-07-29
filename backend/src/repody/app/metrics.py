"""Metrics application — SQL adapters + pure builders."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.db.models import RuleResult, Run, RunStatus
from repody.runtime.metrics.build import (
    MetricsSummary,
    build_kpis,
    build_performance,
    build_stale_alerts,
    build_violations,
    fold_daily_rows,
    week_start,
)
from repody.schemas.metrics import MetricsResponse
from repody.settings import get_settings


async def get_metrics(session: AsyncSession) -> MetricsResponse:
    since = week_start()
    mid = since + timedelta(days=3)
    done = RunStatus.done.value
    running = (RunStatus.running.value, RunStatus.queued.value)

    summary_q = await session.execute(
        select(
            func.count(Run.id).filter(Run.created_at >= since).label("total_week"),
            func.count(Run.id)
            .filter(and_(Run.created_at >= since, Run.status == done))
            .label("done_week"),
            func.count(Run.id)
            .filter(and_(Run.created_at >= since, Run.status == done, Run.overall_status == "passed"))
            .label("passed_week"),
            func.count(Run.id)
            .filter(and_(Run.created_at >= since, Run.status == done, Run.overall_status == "failed"))
            .label("failed_week"),
            func.count(Run.id).filter(Run.status.in_(running)).label("pending"),
            func.count(Run.id)
            .filter(and_(Run.created_at >= since, Run.created_at < mid))
            .label("prev_total"),
            func.count(Run.id)
            .filter(and_(Run.created_at >= since, Run.created_at < mid, Run.status == done))
            .label("prev_done"),
            func.count(Run.id)
            .filter(
                and_(
                    Run.created_at >= since,
                    Run.created_at < mid,
                    Run.status == done,
                    Run.overall_status == "passed",
                )
            )
            .label("prev_passed"),
        )
    )
    row = summary_q.one()
    summary = MetricsSummary(
        total_week=int(row.total_week or 0),
        done_week=int(row.done_week or 0),
        passed_week=int(row.passed_week or 0),
        failed_week=int(row.failed_week or 0),
        pending=int(row.pending or 0),
        prev_total=int(row.prev_total or 0),
        prev_done=int(row.prev_done or 0),
        prev_passed=int(row.prev_passed or 0),
    )

    daily_q = await session.execute(
        select(func.date(Run.created_at), Run.status, Run.overall_status, func.count(Run.id))
        .where(Run.created_at >= since - timedelta(days=7))
        .group_by(func.date(Run.created_at), Run.status, Run.overall_status)
    )
    daily = fold_daily_rows(
        [(day, status, overall, int(count)) for day, status, overall, count in daily_q.all()],
        since=since,
        done_status=done,
    )

    violation_q = await session.execute(
        select(RuleResult.kind, func.count(RuleResult.id))
        .join(Run, Run.id == RuleResult.run_id)
        .where(
            Run.created_at >= since,
            RuleResult.status.in_(("failed", "error")),
        )
        .group_by(RuleResult.kind)
    )
    violation_rows = {row[0]: int(row[1]) for row in violation_q.all()}

    settings = get_settings()
    stale_minutes = max(settings.stale_run_timeout_minutes, 1)
    stale_q = await session.execute(
        select(func.count(Run.id)).where(
            Run.status == RunStatus.running.value,
            Run.started_at.is_not(None),
            Run.started_at < datetime.now(UTC) - timedelta(minutes=stale_minutes),
        )
    )
    stale = int(stale_q.scalar() or 0)

    return MetricsResponse(
        kpis=build_kpis(summary, daily, since),
        performance_series=build_performance(daily, since),
        violation_breakdown=build_violations(violation_rows),
        health_alerts=build_stale_alerts(stale_count=stale),
    )
