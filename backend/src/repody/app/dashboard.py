"""The home dashboard: this week's KPIs against the week before, the queue, recent audits.

Days are UTC (the database session runs in UTC). The pass rate is passed / finished runs,
as on the workflow cards.
"""

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody.app.lifecycle import stuck_running
from repody.app.runs import audit_item
from repody.app.stats import DayCounts, daily_counts, last_days, midnight, pass_rate
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
from repody.schemas.run import AuditListItem

RECENT_AUDITS = 8
FAILED_AUDITS = 3
WORKFLOWS = 6


def _rate(days: list[DayCounts]) -> float:
    return pass_rate(sum(d.passed for d in days), sum(d.done for d in days))


def _kpi(
    kpi_id: KpiId, week: list[date], value: float, previous: float, series: list[float]
) -> Kpi:
    return Kpi(
        id=kpi_id,
        value=value,
        previous=previous,
        series=[KpiPoint(day=d, value=v) for d, v in zip(week, series, strict=True)],
    )


async def _audits(session: AsyncSession, *, failed: bool, limit: int) -> list[AuditListItem]:
    query = select(Run).where(Run.status == "done")
    if failed:
        query = query.where(Run.outcome == "failed")
    return [
        audit_item(run)
        for run in await session.scalars(
            query.order_by(Run.created_at.desc()).limit(limit).options(selectinload(Run.workflow))
        )
    ]


async def get_dashboard(session: AsyncSession) -> Dashboard:
    both_weeks = last_days(14)
    previous_week, week = both_weeks[:7], both_weeks[7:]
    daily = await daily_counts(session, both_weeks[0])
    this_week = [daily.get(d, DayCounts()) for d in week]
    last_week = [daily.get(d, DayCounts()) for d in previous_week]

    queued, running, stale = (
        await session.execute(
            select(
                func.count().filter(Run.status == "queued"),
                func.count().filter(Run.status == "running"),
                func.count().filter(stuck_running(datetime.now(UTC))),
            )
        )
    ).one()
    failures = dict(
        (
            await session.execute(
                select(RuleResult.severity, func.count())
                .join(Run, Run.id == RuleResult.run_id)
                .where(RuleResult.status == "failed", Run.created_at >= midnight(week[0]))
                .group_by(RuleResult.severity)
            )
        ).all()
    )
    total_failures = sum(failures.values())
    return Dashboard(
        kpis=[
            _kpi(
                "auditsWeek",
                week,
                sum(d.runs for d in this_week),
                sum(d.runs for d in last_week),
                [d.runs for d in this_week],
            ),
            _kpi(
                "passRate",
                week,
                _rate(this_week),
                _rate(last_week),
                [_rate([d]) for d in this_week],
            ),
            _kpi(
                "failures",
                week,
                sum(d.failed for d in this_week),
                sum(d.failed for d in last_week),
                [d.failed for d in this_week],
            ),
        ],
        performance_series=[
            DayRuns(day=d, runs=now.runs, prev_runs=before.runs)
            for d, now, before in zip(week, this_week, last_week, strict=True)
        ],
        failures_by_severity=[
            SeverityShare(severity=severity, share=count / total_failures)
            for severity, count in failures.items()
        ],
        stale_runs=stale,
        queue=QueueCounts(queued_runs=queued, running_runs=running),
        recent_audits=await _audits(session, failed=False, limit=RECENT_AUDITS),
        failed_audits=await _audits(session, failed=True, limit=FAILED_AUDITS),
        workflows=await list_workflows(session, limit=WORKFLOWS),
    )
