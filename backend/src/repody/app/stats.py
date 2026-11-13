"""Run statistics shared by the dashboard and the workflow pages: UTC days, daily counts and
the pass rate (passed / finished runs)."""

from datetime import UTC, date, datetime, timedelta
from typing import NamedTuple

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.models import Run


class DayCounts(NamedTuple):
    """Runs created on a day, how many finished, and how many of those passed, need review
    (warning) or failed."""

    runs: int = 0
    done: int = 0
    passed: int = 0
    failed: int = 0
    warning: int = 0


def today() -> date:
    return datetime.now(UTC).date()


def midnight(day: date) -> datetime:
    """The start of a UTC day (the database session runs in UTC too)."""
    return datetime.combine(day, datetime.min.time(), UTC)


def last_days(count: int, *, until: date | None = None) -> list[date]:
    """``count`` consecutive days ending with ``until`` (today), oldest first."""
    end = until or today()
    return [end - timedelta(days=count - 1 - i) for i in range(count)]


def pass_rate(passed: int, done: int) -> float:
    return passed / done if done else 0.0


async def daily_counts(
    session: AsyncSession, since: date, *where: ColumnElement[bool]
) -> dict[date, DayCounts]:
    """Per UTC day from ``since``: runs created, finished, passed and failed."""
    rows = await session.execute(
        select(
            func.date(Run.created_at),
            func.count(),
            func.count().filter(Run.status == "done"),
            func.count().filter(Run.outcome == "passed"),
            func.count().filter(Run.outcome == "failed"),
            func.count().filter(Run.outcome == "warning"),
        )
        .where(Run.created_at >= midnight(since), *where)
        .group_by(func.date(Run.created_at))
    )
    return {day: DayCounts(*counts) for day, *counts in rows}
