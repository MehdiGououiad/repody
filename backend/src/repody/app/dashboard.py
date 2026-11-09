"""The home dashboard: this week's KPIs against the week before, the queue, recent audits."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody.app.runs import audit_item
from repody.app.workflows import list_workflows
from repody.infra.models import RuleResult, Run
from repody.schemas.platform import (
    Dashboard,
    DayRuns,
    Kpi,
    KpiId,
    KpiPoint,
    QueueCounts,
    SeverityShare,
)
from repody.settings import get_settings


class Day(NamedTuple):
    """Runs created on a day, and how many of them passed or failed."""

    runs: int = 0
    passed: int = 0
    failed: int = 0


async def _daily(session: AsyncSession, since: datetime) -> dict[date, Day]:
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
    return {day: Day(runs, passed, failed) for day, runs, passed, failed in rows}


async def get_dashboard(session: AsyncSession) -> Dashboard:
    today = datetime.now(UTC).date()
    week = [today - timedelta(days=6 - i) for i in range(7)]
    previous_week = [d - timedelta(days=7) for d in week]
    daily = await _daily(session, datetime.combine(previous_week[0], datetime.min.time(), UTC))

    this_week = [daily.get(d, Day()) for d in week]
    last_week = [daily.get(d, Day()) for d in previous_week]

    def pass_rate(days: list[Day]) -> float:
        runs = sum(d.runs for d in days)
        return sum(d.passed for d in days) / runs if runs else 0.0

    queued, running = (
        await session.execute(
            select(
                func.count().filter(Run.status == "queued"),
                func.count().filter(Run.status == "running"),
            )
        )
    ).one()

    def kpi(kpi_id: KpiId, value: float, previous: float, series: list[int]) -> Kpi:
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
    failure_counts = dict(failures.all())
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
            kpi(
                "auditsWeek",
                sum(d.runs for d in this_week),
                sum(d.runs for d in last_week),
                [d.runs for d in this_week],
            ),
            kpi(
                "passRate",
                pass_rate(this_week),
                pass_rate(last_week),
                [d.passed for d in this_week],
            ),
            kpi(
                "failures",
                sum(d.failed for d in this_week),
                sum(d.failed for d in last_week),
                [d.failed for d in this_week],
            ),
            kpi("pendingReview", queued + running, 0, []),  # a live count: no history
        ],
        performance_series=[
            DayRuns(day=d.strftime("%a"), runs=now.runs, prev_runs=before.runs)
            for d, now, before in zip(week, this_week, last_week, strict=True)
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
