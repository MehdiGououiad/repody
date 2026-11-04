"""The home dashboard: this week's KPIs against the week before, the queue, recent audits."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody.app.runs import audit_item
from repody.app.workflows import list_workflows
from repody.infra.models import RuleResult, Run
from repody.schemas.platform import Dashboard, DayRuns, Kpi, KpiPoint, QueueCounts, SeverityShare
from repody.settings import get_settings


async def _daily(session: AsyncSession, since: datetime) -> dict[date, tuple[int, int, int]]:
    """``(runs, passed, failed)`` per day."""
    rows = await session.execute(
        select(
            func.date(Run.created_at),
            func.count(),
            func.count().filter(Run.outcome == "passed"),
            func.count().filter(Run.outcome == "failed"),
        )
        .where(Run.created_at >= since)
        .group_by(func.date(Run.created_at))
    )
    return {day: (runs, passed, failed) for day, runs, passed, failed in rows.tuples()}


async def get_dashboard(session: AsyncSession) -> Dashboard:
    today = datetime.now(UTC).date()
    week = [today - timedelta(days=6 - i) for i in range(7)]
    previous_week = [d - timedelta(days=7) for d in week]
    daily = await _daily(session, datetime.combine(previous_week[0], datetime.min.time(), UTC))

    def column(days: list[date], index: int) -> list[float]:
        return [float(daily.get(d, (0, 0, 0))[index]) for d in days]

    def rate(days: list[date]) -> float:
        runs, passed = sum(column(days, 0)), sum(column(days, 1))
        return passed / runs if runs else 0.0

    queued, running = (
        await session.execute(
            select(
                func.count().filter(Run.status == "queued"),
                func.count().filter(Run.status == "running"),
            )
        )
    ).one()

    def kpi(kpi_id, value: float, previous: float, series: list[float]) -> Kpi:
        return Kpi(
            id=kpi_id,
            value=value,
            previous=previous,
            series=[
                KpiPoint(day=d.isoformat(), value=v) for d, v in zip(week, series, strict=False)
            ],
        )

    failures = await session.execute(
        select(RuleResult.severity, func.count())
        .join(Run, Run.id == RuleResult.run_id)
        .where(
            RuleResult.status == "failed",
            Run.created_at >= datetime.combine(week[0], datetime.min.time(), UTC),
        )
        .group_by(RuleResult.severity)
    )
    failure_counts = dict(failures.tuples().all())
    total_failures = sum(failure_counts.values())

    stale_before = datetime.now(UTC) - timedelta(minutes=get_settings().run_timeout_minutes)
    stale = await session.scalar(
        select(func.count()).where(Run.status == "running", Run.started_at < stale_before)
    )
    recent = await session.scalars(
        select(Run)
        .where(Run.status == "done")
        .order_by(Run.created_at.desc())
        .limit(50)
        .options(selectinload(Run.workflow))
    )
    return Dashboard(
        kpis=[
            kpi("auditsWeek", sum(column(week, 0)), sum(column(previous_week, 0)), column(week, 0)),
            kpi("passRate", rate(week), rate(previous_week), column(week, 1)),
            kpi("failures", sum(column(week, 2)), sum(column(previous_week, 2)), column(week, 2)),
            kpi("pendingReview", queued + running, 0, []),  # a live count: no history
        ],
        performance_series=[
            DayRuns(
                day=d.strftime("%a"),
                runs=int(daily.get(d, (0, 0, 0))[0]),
                prev_runs=int(daily.get(p, (0, 0, 0))[0]),
            )
            for d, p in zip(week, previous_week, strict=True)
        ],
        failures_by_severity=[
            SeverityShare(severity=severity, share=count / total_failures)
            for severity, count in failure_counts.items()
        ],
        stale_runs=stale or 0,
        queue=QueueCounts(queued_runs=queued, running_runs=running),
        audits=[audit_item(run) for run in recent],
        workflows=await list_workflows(session),
    )
