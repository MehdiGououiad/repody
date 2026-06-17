from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db.models import RuleResult, Run, RunStatus
from audit_workbench.schemas.metrics import (
    HealthAlert,
    KpiMetric,
    KpiSeriesPoint,
    MetricsResponse,
    PerformancePoint,
    ViolationBreakdown,
)

_DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _week_start() -> datetime:
    now = datetime.now(UTC)
    return (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)


async def _daily_run_counts(
    session: AsyncSession,
    *,
    since: datetime,
    status: str | None = None,
    overall: str | None = None,
) -> dict[str, int]:
    stmt = (
        select(func.date(Run.created_at), func.count(Run.id))
        .where(Run.created_at >= since)
        .group_by(func.date(Run.created_at))
    )
    if status:
        stmt = stmt.where(Run.status == status)
    if overall:
        stmt = stmt.where(Run.overall_status == overall)
    rows = await session.execute(stmt)
    return {str(row[0]): int(row[1]) for row in rows.all()}


def _series_from_counts(counts: dict[str, int], since: datetime) -> list[KpiSeriesPoint]:
    return [
        KpiSeriesPoint(
            day=_DAY_LABELS[i % 7],
            value=float(counts.get(str((since + timedelta(days=i)).date()), 0)),
        )
        for i in range(7)
    ]


def _delta(current: float, previous: float) -> tuple[float, str, bool]:
    if previous <= 0:
        return 0.0, "absolute", current >= 0
    change = ((current - previous) / previous) * 100
    return round(abs(change), 1), "percent", change >= 0


async def get_metrics(session: AsyncSession) -> MetricsResponse:
    since = _week_start()
    mid = since + timedelta(days=3)

    total_week_q = await session.execute(select(func.count(Run.id)).where(Run.created_at >= since))
    total_week = int(total_week_q.scalar() or 0)

    done_q = await session.execute(
        select(func.count(Run.id)).where(
            Run.status == RunStatus.done.value,
            Run.created_at >= since,
        )
    )
    done_week = int(done_q.scalar() or 0)

    passed_q = await session.execute(
        select(func.count(Run.id)).where(
            Run.status == RunStatus.done.value,
            Run.overall_status == "passed",
            Run.created_at >= since,
        )
    )
    passed_week = int(passed_q.scalar() or 0)

    failed_q = await session.execute(
        select(func.count(Run.id)).where(
            Run.status == RunStatus.done.value,
            Run.overall_status == "failed",
            Run.created_at >= since,
        )
    )
    failed_week = int(failed_q.scalar() or 0)

    running_q = await session.execute(
        select(func.count(Run.id)).where(
            Run.status.in_((RunStatus.running.value, RunStatus.queued.value))
        )
    )
    pending = int(running_q.scalar() or 0)

    rate = (passed_week / done_week) if done_week else 0.0

    prev_done_q = await session.execute(
        select(func.count(Run.id)).where(
            Run.status == RunStatus.done.value,
            Run.created_at >= since,
            Run.created_at < mid,
        )
    )
    prev_done = int(prev_done_q.scalar() or 0)
    prev_passed_q = await session.execute(
        select(func.count(Run.id)).where(
            Run.status == RunStatus.done.value,
            Run.overall_status == "passed",
            Run.created_at >= since,
            Run.created_at < mid,
        )
    )
    prev_passed = int(prev_passed_q.scalar() or 0)
    prev_rate = (prev_passed / prev_done) if prev_done else 0.0

    week_counts = await _daily_run_counts(session, since=since)
    passed_counts = await _daily_run_counts(
        session, since=since, status=RunStatus.done.value, overall="passed"
    )
    failed_counts = await _daily_run_counts(
        session, since=since, status=RunStatus.done.value, overall="failed"
    )

    audits_delta, audits_unit, audits_up = _delta(float(total_week), float(total_week // 2))
    rate_delta, rate_unit, rate_up = _delta(rate * 100, prev_rate * 100)

    kpis = [
        KpiMetric(
            id="auditsWeek",
            label="Audits this week",
            value=str(total_week),
            raw_value=float(total_week),
            delta=audits_delta,
            delta_unit=audits_unit,
            direction="up" if audits_up else "down",
            positive=audits_up,
            series=_series_from_counts(week_counts, since),
            icon="account_tree",
        ),
        KpiMetric(
            id="passRate",
            label="Pass rate",
            value=f"{rate * 100:.1f}%",
            raw_value=rate,
            delta=rate_delta,
            delta_unit=rate_unit,
            direction="up" if rate_up else "down",
            positive=rate_up,
            series=_series_from_counts(passed_counts, since),
            icon="check_circle",
        ),
        KpiMetric(
            id="failures",
            label="Rule failures",
            value=str(failed_week),
            raw_value=float(failed_week),
            delta=float(failed_week),
            delta_unit="absolute",
            direction="up" if failed_week else "down",
            positive=failed_week == 0,
            series=_series_from_counts(failed_counts, since),
            icon="gavel",
        ),
        KpiMetric(
            id="pendingReview",
            label="Pending review",
            value=str(pending),
            raw_value=float(pending),
            delta=float(pending),
            delta_unit="absolute",
            direction="down" if pending == 0 else "up",
            positive=pending == 0,
            series=_series_from_counts(week_counts, since),
            icon="timer",
        ),
    ]

    prev_week_counts = await _daily_run_counts(session, since=since - timedelta(days=7))
    performance = [
        PerformancePoint(
            day=_DAY_LABELS[i % 7],
            runs=int(week_counts.get(str((since + timedelta(days=i)).date()), 0)),
            prev_runs=int(
                prev_week_counts.get(str((since - timedelta(days=7) + timedelta(days=i)).date()), 0)
            ),
        )
        for i in range(7)
    ]

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
    violation_total = sum(violation_rows.values()) or 1
    violations = []
    color_map = {"logic": "danger", "llm": "warning", "format": "info"}
    for kind, count in violation_rows.items():
        violations.append(
            ViolationBreakdown(
                type=kind or "other",
                share=round((count / violation_total) * 100, 1),
                color=color_map.get(kind or "", "neutral"),
            )
        )
    if not violations:
        violations = [ViolationBreakdown(type="none", share=100.0, color="neutral")]

    alerts: list[HealthAlert] = []
    stale_q = await session.execute(
        select(func.count(Run.id)).where(
            Run.status == RunStatus.running.value,
            Run.started_at.is_not(None),
            Run.started_at < datetime.now(UTC) - timedelta(minutes=15),
        )
    )
    stale = int(stale_q.scalar() or 0)
    if stale:
        alerts.append(
            HealthAlert(
                id="stale-runs",
                severity="warning",
                title_key="alerts.stale.title",
                detail_key="alerts.stale.detail",
                href="/audits",
            )
        )

    return MetricsResponse(
        kpis=kpis,
        performance_series=performance,
        violation_breakdown=violations,
        health_alerts=alerts,
    )
