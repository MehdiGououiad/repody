"""Pure metrics builders — no SQL / session."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from repody.schemas.metrics import (
    HealthAlert,
    KpiMetric,
    KpiSeriesPoint,
    PerformancePoint,
    ViolationBreakdown,
)

_DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_VIOLATION_COLORS = {"logic": "danger", "llm": "warning", "format": "info"}


@dataclass(frozen=True, slots=True)
class MetricsSummary:
    total_week: int
    done_week: int
    passed_week: int
    failed_week: int
    pending: int
    prev_total: int
    prev_done: int
    prev_passed: int


@dataclass(frozen=True, slots=True)
class DailyCounts:
    week_counts: dict[str, int]
    passed_counts: dict[str, int]
    failed_counts: dict[str, int]
    prev_week_counts: dict[str, int]


def week_start(now: datetime | None = None) -> datetime:
    current = now or datetime.now(UTC)
    return (current - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)


def series_from_counts(counts: dict[str, int], since: datetime) -> list[KpiSeriesPoint]:
    return [
        KpiSeriesPoint(
            day=_DAY_LABELS[i % 7],
            value=float(counts.get(str((since + timedelta(days=i)).date()), 0)),
        )
        for i in range(7)
    ]


def delta(current: float, previous: float) -> tuple[float, str, bool]:
    if previous <= 0:
        return 0.0, "absolute", current >= 0
    change = ((current - previous) / previous) * 100
    return round(abs(change), 1), "percent", change >= 0


def build_kpis(summary: MetricsSummary, daily: DailyCounts, since: datetime) -> list[KpiMetric]:
    rate = (summary.passed_week / summary.done_week) if summary.done_week else 0.0
    prev_rate = (summary.prev_passed / summary.prev_done) if summary.prev_done else 0.0
    audits_delta, audits_unit, audits_up = delta(
        float(summary.total_week), float(summary.prev_total)
    )
    rate_delta, rate_unit, rate_up = delta(rate * 100, prev_rate * 100)
    return [
        KpiMetric(
            id="auditsWeek",
            label="Audits this week",
            value=str(summary.total_week),
            raw_value=float(summary.total_week),
            delta=audits_delta,
            delta_unit=audits_unit,
            direction="up" if audits_up else "down",
            positive=audits_up,
            series=series_from_counts(daily.week_counts, since),
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
            series=series_from_counts(daily.passed_counts, since),
            icon="check_circle",
        ),
        KpiMetric(
            id="failures",
            label="Rule failures",
            value=str(summary.failed_week),
            raw_value=float(summary.failed_week),
            delta=float(summary.failed_week),
            delta_unit="absolute",
            direction="up" if summary.failed_week else "down",
            positive=summary.failed_week == 0,
            series=series_from_counts(daily.failed_counts, since),
            icon="gavel",
        ),
        KpiMetric(
            id="pendingReview",
            label="Pending review",
            value=str(summary.pending),
            raw_value=float(summary.pending),
            delta=float(summary.pending),
            delta_unit="absolute",
            direction="down" if summary.pending == 0 else "up",
            positive=summary.pending == 0,
            series=series_from_counts(daily.week_counts, since),
            icon="timer",
        ),
    ]


def build_performance(daily: DailyCounts, since: datetime) -> list[PerformancePoint]:
    return [
        PerformancePoint(
            day=_DAY_LABELS[i % 7],
            runs=int(daily.week_counts.get(str((since + timedelta(days=i)).date()), 0)),
            prev_runs=int(
                daily.prev_week_counts.get(
                    str((since - timedelta(days=7) + timedelta(days=i)).date()), 0
                )
            ),
        )
        for i in range(7)
    ]


def build_violations(violation_rows: dict[str | None, int]) -> list[ViolationBreakdown]:
    violation_total = sum(violation_rows.values()) or 1
    violations = [
        ViolationBreakdown(
            type=kind or "other",
            share=round((count / violation_total) * 100, 1),
            color=_VIOLATION_COLORS.get(kind or "", "neutral"),
        )
        for kind, count in violation_rows.items()
    ]
    if not violations:
        return [ViolationBreakdown(type="none", share=100.0, color="neutral")]
    return violations


def build_stale_alerts(*, stale_count: int) -> list[HealthAlert]:
    if not stale_count:
        return []
    return [
        HealthAlert(
            id="stale-runs",
            severity="warning",
            title_key="alerts.stale.title",
            detail_key="alerts.stale.detail",
            href="/audits",
        )
    ]


def fold_daily_rows(
    rows: list[tuple[object, str, str | None, int]],
    *,
    since: datetime,
    done_status: str,
) -> DailyCounts:
    week_counts: dict[str, int] = {}
    passed_counts: dict[str, int] = {}
    failed_counts: dict[str, int] = {}
    prev_week_counts: dict[str, int] = {}
    since_date = since.date()
    prev_start_date = (since - timedelta(days=7)).date()

    for day, status, overall, count in rows:
        day_str = str(day)
        day_date = day if isinstance(day, date) else datetime.fromisoformat(day_str).date()
        value = int(count)
        if day_date >= since_date:
            week_counts[day_str] = week_counts.get(day_str, 0) + value
            if status == done_status and overall == "passed":
                passed_counts[day_str] = passed_counts.get(day_str, 0) + value
            if status == done_status and overall == "failed":
                failed_counts[day_str] = failed_counts.get(day_str, 0) + value
        elif day_date >= prev_start_date:
            prev_week_counts[day_str] = prev_week_counts.get(day_str, 0) + value

    return DailyCounts(
        week_counts=week_counts,
        passed_counts=passed_counts,
        failed_counts=failed_counts,
        prev_week_counts=prev_week_counts,
    )
