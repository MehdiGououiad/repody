"""Access requests: a prospect asks for an account on the site; a platform admin approves it (a
client, a user, starting credits) or declines it."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from repody.schemas.admin import CLIENT_SLUG, ClientRole, Email, TemporaryPassword
from repody.schemas.common import CamelModel

AccessStatus = Literal["new", "approved", "declined"]
Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Long = Annotated[str, StringConstraints(strip_whitespace=True, max_length=4000)]


class AccessRequestIn(CamelModel):
    name: Short
    email: Email
    company: Short
    sector: Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] = ""
    message: Long = ""
    locale: Literal["fr", "en"] = "fr"
    consent: Literal[True] = Field(description="The prospect agrees to be contacted about it.")
    turnstile_token: Annotated[str, StringConstraints(max_length=4096)] = ""


class AccessRequestOut(CamelModel):
    id: str
    name: str
    email: str
    company: str
    sector: str
    message: str
    locale: str
    status: AccessStatus
    note: str
    account: str | None
    decided_by: str | None
    created_at: datetime
    decided_at: datetime | None


class AccessApprove(CamelModel):
    slug: str = Field(
        pattern=CLIENT_SLUG, description="The client is client-<slug> (created if new)."
    )
    role: ClientRole = "admin"
    credits: int = Field(default=200, ge=0, le=100_000)


class AccessDecline(CamelModel):
    note: Long = ""


class AccessApproved(CamelModel):
    request: AccessRequestOut
    invited: TemporaryPassword
