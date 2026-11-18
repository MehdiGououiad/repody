"""The home dashboard: this week's KPIs against the week before, the queue, recent audits.

Days are UTC (the database session runs in UTC). The pass rate is passed / finished runs,
as on the workflow cards.
"""

from datetime import date, datetime

from sqlalchemy import ColumnElement, Float, cast, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from repody.app.runs import audit_item
from repody.app.scope import visible_runs
from repody.app.stats import DayCounts, daily_counts, last_days, midnight, pass_rate
from repody.app.workflows import list_workflows
from repody.infra.models import RuleResult, Run, RunDocument
from repody.schemas.platform import (
    Dashboard,
    DayRuns,
    DocumentStats,
    DocumentTypeCount,
    DurationStats,
    HourRuns,
    Kpi,
    KpiId,
    KpiPoint,
    QueueCounts,
    SeverityShare,
    SourceCounts,
    WorkflowActivity,
)
from repody.schemas.run import AuditListItem

RECENT_AUDITS = 8
FAILED_AUDITS = 6
WORKFLOWS = 6
TOP = 5


def _duration_ms() -> ColumnElement[float]:
    """A finished run's time from start to finish, in milliseconds."""
    return cast(func.extract("epoch", Run.finished_at - Run.started_at) * 1000, Float)


def _ms(value: float | None) -> int:
    return round(value or 0)


async def timing(
    session: AsyncSession, since: datetime, mine: ColumnElement[bool] | None = None
) -> DurationStats:
    mine = true() if mine is None else mine
    duration = _duration_ms()
    median, p95, extraction = (
        await session.execute(
            select(
                func.percentile_cont(0.5).within_group(duration),
                func.percentile_cont(0.95).within_group(duration),
                func.percentile_cont(0.5).within_group(Run.extraction_ms),
            ).where(
                Run.status == "done", Run.created_at >= since, Run.started_at.is_not(None), mine
            )
        )
    ).one()
    return DurationStats(
        median_ms=_ms(median), p95_ms=_ms(p95), extraction_median_ms=_ms(extraction)
    )


async def queue_counts(session: AsyncSession) -> QueueCounts:
    """The platform's runs waiting and in progress (every account's: they explain a wait)."""
    queued, running = (
        await session.execute(
            select(
                func.count().filter(Run.status == "queued"),
                func.count().filter(Run.status == "running"),
            ).where(Run.status.in_(("queued", "running")))  # the status index, not the table
        )
    ).one()
    return QueueCounts(queued_runs=queued, running_runs=running)


async def _sources(
    session: AsyncSession, since: datetime, mine: ColumnElement[bool]
) -> SourceCounts:
    api, test = (
        await session.execute(
            select(
                func.count().filter(Run.source == "api"),
                func.count().filter(Run.source == "test"),
            ).where(Run.created_at >= since, mine)
        )
    ).one()
    return SourceCounts(api=api, test=test)


async def _hourly(
    session: AsyncSession, since: datetime, mine: ColumnElement[bool]
) -> list[HourRuns]:
    hour = func.extract("hour", Run.created_at)
    rows = await session.execute(
        select(func.date(Run.created_at), hour, func.count())
        .where(Run.created_at >= since, mine)
        .group_by(func.date(Run.created_at), hour)
    )
    return [HourRuns(day=day, hour=int(h), runs=runs) for day, h, runs in rows]


async def _documents(
    session: AsyncSession, since: datetime, mine: ColumnElement[bool]
) -> DocumentStats:
    pages = func.coalesce(func.sum(RunDocument.extraction["pagesRendered"].as_integer()), 0)
    rows = (
        await session.execute(
            select(RunDocument.document_type, func.count(), pages)
            .join(Run, Run.id == RunDocument.run_id)
            .where(Run.created_at >= since, mine)
            .group_by(RunDocument.document_type)
            .order_by(func.count().desc(), RunDocument.document_type)
        )
    ).all()
    by_type = [
        DocumentTypeCount(document_type=doc_type or "—", documents=count, pages=page_count)
        for doc_type, count, page_count in rows
    ]
    return DocumentStats(
        documents=sum(t.documents for t in by_type),
        pages=sum(t.pages for t in by_type),
        by_type=by_type[:TOP],
    )


async def _workflow_activity(
    session: AsyncSession, week: list[date], workflow_ids: list[str], mine: ColumnElement[bool]
) -> list[WorkflowActivity]:
    if not workflow_ids:
        return []
    since = midnight(week[0])
    per_day = await session.execute(
        select(Run.workflow_id, func.date(Run.created_at), func.count())
        .where(Run.workflow_id.in_(workflow_ids), Run.created_at >= since, mine)
        .group_by(Run.workflow_id, func.date(Run.created_at))
    )
    counts: dict[str, dict[date, int]] = {}
    for wf_id, day, count in per_day:
        counts.setdefault(wf_id, {})[day] = count
    medians = dict(
        (
            await session.execute(
                select(Run.workflow_id, func.percentile_cont(0.5).within_group(_duration_ms()))
                .where(
                    Run.workflow_id.in_(workflow_ids),
                    mine,
                    Run.status == "done",
                    Run.created_at >= since,
                    Run.started_at.is_not(None),
                )
                .group_by(Run.workflow_id)
            )
        ).all()
    )
    return [
        WorkflowActivity(
            workflow_id=wf_id,
            runs=[counts.get(wf_id, {}).get(d, 0) for d in week],
            median_ms=_ms(medians.get(wf_id)),
        )
        for wf_id in workflow_ids
    ]


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


async def _audits(
    session: AsyncSession, mine: ColumnElement[bool], *, failed: bool, limit: int
) -> list[AuditListItem]:
    query = select(Run).where(Run.status == "done", mine)
    if failed:
        # The review queue: rejected runs and runs that need a person (warning).
        query = query.where(Run.outcome.in_(("failed", "warning")))
    return [
        audit_item(run)
        for run in await session.scalars(
            query.order_by(Run.created_at.desc())
            .limit(limit)
            .options(
                selectinload(Run.workflow),
                selectinload(Run.documents).load_only(RunDocument.file_name, RunDocument.position),
                selectinload(Run.rule_results).load_only(
                    RuleResult.name, RuleResult.status, RuleResult.severity
                ),
            )
        )
    ]


async def get_dashboard(session: AsyncSession, *, account: str | None = None) -> Dashboard:
    """The account's runs and workflows; the queue counts are the platform's."""
    mine = visible_runs(account)
    both_weeks = last_days(14)
    previous_week, week = both_weeks[:7], both_weeks[7:]
    daily = await daily_counts(session, both_weeks[0], mine)
    this_week = [daily.get(d, DayCounts()) for d in week]
    last_week = [daily.get(d, DayCounts()) for d in previous_week]

    failures = dict(
        (
            await session.execute(
                select(RuleResult.severity, func.count())
                .join(Run, Run.id == RuleResult.run_id)
                .where(RuleResult.status == "failed", Run.created_at >= midnight(week[0]), mine)
                .group_by(RuleResult.severity)
            )
        ).all()
    )
    total_failures = sum(failures.values())
    since = midnight(week[0])
    workflows = await list_workflows(session, limit=WORKFLOWS, account=account)
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
            DayRuns(day=d, runs=c.runs, passed=c.passed, warning=c.warning, failed=c.failed)
            for d, c in ((d, daily.get(d, DayCounts())) for d in both_weeks)
        ],
        timing=await timing(session, since, mine),
        sources=await _sources(session, since, mine),
        hourly=await _hourly(session, since, mine),
        documents=await _documents(session, since, mine),
        workflow_activity=await _workflow_activity(session, week, [w.id for w in workflows], mine),
        failures_by_severity=[
            SeverityShare(severity=severity, share=count / total_failures)
            for severity, count in failures.items()
        ],
        queue=await queue_counts(session),
        recent_audits=await _audits(session, mine, failed=False, limit=RECENT_AUDITS),
        failed_audits=await _audits(session, mine, failed=True, limit=FAILED_AUDITS),
        workflows=workflows,
    )
