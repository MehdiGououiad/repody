"""Unit tests for pure metrics builders."""

from __future__ import annotations

from datetime import UTC, datetime

from repody.runtime.metrics.build import (
    MetricsSummary,
    DailyCounts,
    build_kpis,
    build_stale_alerts,
    build_violations,
    delta,
    week_start,
)


def test_delta_percent_and_absolute() -> None:
    assert delta(110, 100) == (10.0, "percent", True)
    assert delta(5, 0) == (0.0, "absolute", True)


def test_week_start_is_midnight() -> None:
    now = datetime(2026, 7, 15, 14, 30, tzinfo=UTC)
    start = week_start(now)
    assert start.hour == 0
    assert start.minute == 0
    assert (now.date() - start.date()).days == 6


def test_build_kpis_pass_rate() -> None:
    summary = MetricsSummary(
        total_week=10,
        done_week=10,
        passed_week=8,
        failed_week=2,
        pending=1,
        prev_total=5,
        prev_done=5,
        prev_passed=4,
    )
    daily = DailyCounts({}, {}, {}, {})
    kpis = build_kpis(summary, daily, week_start())
    pass_rate = next(k for k in kpis if k.id == "passRate")
    assert pass_rate.raw_value == 0.8
    assert pass_rate.value == "80.0%"


def test_build_violations_empty_default() -> None:
    assert build_violations({})[0].type == "none"


def test_stale_alerts() -> None:
    assert build_stale_alerts(stale_count=0) == []
    assert build_stale_alerts(stale_count=2)[0].id == "stale-runs"
