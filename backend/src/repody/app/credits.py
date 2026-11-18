"""Credits: every run is metered, and paid for by its account when AUDIT_CREDITS_ENFORCED is on.

1 credit = 1 page sent to the model, plus AUDIT_CREDIT_RUN_FEE per run. A run's account is its
workflow's (a client company); a workflow without one (shared, or made by a platform admin) runs
on the ``deployment`` account, which is metered but never refused.

A run holds its estimate (its files' pages) when it is queued, in the transaction that saves it,
under a per-account lock: two runs started together cannot both spend the last credits. It is
settled once, in the transaction that ends it: done pays the pages it sent the model (those of a
request that timed out too, not those of a file that could not be read); failed after it
started pays its estimate (the model may have worked on every page; an admin can give credits
back with a grant); failed before it started (cancelled while queued, never dispatched) pays
nothing. The ledger is one table (repody.infra.models.CreditEntry): balance = sum of amounts.
"""

from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.errors import AppError
from repody.infra.models import CreditEntry, Run, new_id
from repody.schemas.credits import AccountUsage, Credits, UsageReport
from repody.settings import get_settings

log = structlog.get_logger(__name__)

DEPLOYMENT = "deployment"
NO_CREDITS = (
    "Not enough credits: this run needs {needed} and {account} has {balance} left."
    " Contact us for credits to continue."
)


def payer(workflow_account: str | None) -> str:
    return workflow_account or DEPLOYMENT


def _enforced_for(account: str) -> bool:
    return get_settings().credits_enforced and account != DEPLOYMENT


async def _lock(session: AsyncSession, account: str) -> None:
    """Serialize credit changes of one account until the transaction ends."""
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:a))"), {"a": account})


async def balances(session: AsyncSession, account: str) -> tuple[int, int]:
    """``(available, held)``: what the account can still spend (holds already taken off), and
    what its runs in progress hold."""
    available, held = (
        await session.execute(
            select(
                func.coalesce(func.sum(CreditEntry.amount), 0),
                func.coalesce(-func.sum(CreditEntry.amount).filter(CreditEntry.pending), 0),
            ).where(CreditEntry.account_id == account)
        )
    ).one()
    return int(available), int(held)


async def credits_of(session: AsyncSession, account: str | None) -> Credits:
    available, held = await balances(session, account) if account else (0, 0)
    settings = get_settings()
    enforced = settings.credits_enforced and account is not None
    low = enforced and available < settings.credit_low_balance
    return Credits(account=account, balance=available, held=held, enforced=enforced, low=low)


def run_cost(pages: int) -> int:
    return pages + get_settings().credit_run_fee


async def can_pay(session: AsyncSession, account: str, cost: int) -> None:
    """402 when the account cannot pay ``cost`` (enforced accounts only). Without the lock: a
    fast answer before uploading; ``hold`` decides under the lock."""
    if not _enforced_for(account):
        return
    available, _held = await balances(session, account)
    if available < cost:
        log.warning("run_refused_no_credits", account=account, needed=cost, balance=available)
        raise AppError(402, NO_CREDITS.format(needed=cost, account=account, balance=available))


async def hold(session: AsyncSession, run: Run, account: str, cost: int, actor: str) -> None:
    """Hold the run's estimate on its account (402 when it cannot pay). The caller commits,
    in the transaction that saves the run."""
    await _lock(session, account)
    await can_pay(session, account, cost)
    session.add(
        CreditEntry(
            id=new_id("cr"),
            account_id=account,
            kind="run",
            amount=-cost,
            pending=True,
            run_id=run.id,
            actor=actor,
        )
    )


async def settle_done(session: AsyncSession, run_id: str, *, pages: int, model_ms: int) -> None:
    """The run is done: it pays the pages it sent the model, also those of a request that timed
    out (the model may have worked on them all along), never those of a document that could not
    be read or a request the server refused. The caller commits (with the run)."""
    await session.execute(
        update(CreditEntry)
        .where(CreditEntry.run_id == run_id, CreditEntry.pending)
        .values(
            amount=-run_cost(pages),
            pages=pages,
            model_ms=model_ms,
            pending=False,
            settled_at=datetime.now(UTC),
        )
    )
    log.info("run_settled", run_id=run_id, outcome="done", pages=pages, model_ms=model_ms)


async def settle_failed(session: AsyncSession, run_id: str) -> None:
    """The run failed: it keeps its estimate if it started, else pays nothing. The caller
    commits (with the run)."""
    started = await session.scalar(select(Run.started_at).where(Run.id == run_id))
    values: dict[str, object] = {"pending": False, "settled_at": datetime.now(UTC)}
    if started is None:
        values["amount"] = 0
    await session.execute(
        update(CreditEntry).where(CreditEntry.run_id == run_id, CreditEntry.pending).values(values)
    )
    log.info(
        "run_settled",
        run_id=run_id,
        outcome="failed",
        charged="estimate" if started else "nothing",
    )


async def grant(session: AsyncSession, account: str, amount: int, note: str, actor: str) -> Credits:
    await _lock(session, account)
    session.add(
        CreditEntry(
            id=new_id("cr"), account_id=account, kind="grant", amount=amount, note=note, actor=actor
        )
    )
    await session.flush()
    balance = await credits_of(session, account)
    log.info(
        "credits_granted", account=account, amount=amount, actor=actor, balance=balance.balance
    )
    return balance


async def usage(
    session: AsyncSession,
    *,
    account: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> UsageReport:
    """Each account's balance (now) and its settled runs between ``since`` and ``until``."""
    entry = CreditEntry
    in_window = entry.kind == "run"
    if since:
        in_window &= entry.created_at >= since
    if until:
        in_window &= entry.created_at < until
    settled_run = in_window & ~entry.pending
    query = (
        select(
            entry.account_id,
            func.sum(entry.amount),
            -func.coalesce(func.sum(entry.amount).filter(entry.pending), 0),
            func.coalesce(func.sum(entry.amount).filter(entry.kind == "grant"), 0),
            func.count().filter(settled_run),
            func.coalesce(func.sum(entry.pages).filter(settled_run), 0),
            func.coalesce(func.sum(entry.model_ms).filter(settled_run), 0),
            func.max(entry.created_at),
        )
        .group_by(entry.account_id)
        .order_by(entry.account_id)
    )
    if account is not None:
        query = query.where(entry.account_id == account)
    rows = await session.execute(query)
    return UsageReport(
        since=since,
        until=until,
        accounts=[
            AccountUsage(
                account=acc,
                balance=int(balance),
                held=int(held),
                granted=int(granted),
                runs=runs,
                pages=int(pages),
                model_ms=int(model_ms),
                last_activity=last,
            )
            for acc, balance, held, granted, runs, pages, model_ms, last in rows
        ],
    )
