"""Credits: what a run costs, what an account has left, and who granted what."""

from datetime import datetime
from typing import Literal

from pydantic import Field

from repody.schemas.common import CamelModel

CreditKind = Literal["grant", "run"]


class Credits(CamelModel):
    """The caller's account and balance; ``enforced`` says whether runs are refused at zero."""

    account: str | None = Field(
        description="client-<name>, or None for a caller outside any client (sees everything)."
    )
    balance: int = Field(description="Credits left (1 credit = 1 page sent to the model).")
    held: int = Field(description="Credits held by runs still in progress.")
    enforced: bool
    low: bool = Field(default=False, description="Below AUDIT_CREDIT_LOW_BALANCE, enforced.")


class AccountUsage(CamelModel):
    account: str
    balance: int
    held: int
    granted: int
    runs: int = Field(description="Settled runs.")
    pages: int = Field(description="Pages sent to the model by settled runs.")
    model_ms: int = Field(description="Extraction time of settled runs.")
    last_activity: datetime | None


class UsageReport(CamelModel):
    since: datetime | None
    until: datetime | None
    accounts: list[AccountUsage]
