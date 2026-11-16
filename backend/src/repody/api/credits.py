"""Credits: grant them to a client company, read balances and usage."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from repody.api.deps import AccountScope, SessionDep, require
from repody.app import credits
from repody.infra.auth import User
from repody.schemas.credits import Credits, GrantIn, UsageReport

router = APIRouter(prefix="/credits", tags=["credits"])


@router.post("/grants", status_code=201)
async def grant(
    body: GrantIn, session: SessionDep, user: Annotated[User, require("credits:grant")]
) -> Credits:
    """Add credits to an account (a negative amount takes them back); its new balance."""
    balance = await credits.grant(session, body.account, body.amount, body.note, user.subject)
    await session.commit()
    return balance


@router.get("/usage", dependencies=[require("metrics:read")])
async def usage(
    session: SessionDep,
    account: AccountScope,
    since: Annotated[datetime | None, Query(description="Runs queued from (ISO 8601).")] = None,
    until: Annotated[datetime | None, Query(description="Runs queued before.")] = None,
) -> UsageReport:
    """Each account's balance and the runs it paid for: the caller's account, or every account
    for a caller outside any client (a platform admin)."""
    return await credits.usage(session, account=account, since=since, until=until)
