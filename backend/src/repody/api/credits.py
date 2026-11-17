"""Credits: read balances and usage (a platform admin grants them in the admin area,
``POST /v1/admin/clients/{account}/credits``, which records who did it)."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from repody.api.deps import AccountScope, SessionDep, require
from repody.app import credits
from repody.schemas.credits import UsageReport

router = APIRouter(prefix="/credits", tags=["credits"])


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
