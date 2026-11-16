"""The admin area: client companies, their users, credits, spend and the audit log."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, StringConstraints

from repody.schemas.common import CamelModel, Name, Text
from repody.schemas.credits import CreditKind

ClientRole = Literal["viewer", "operator", "admin"]
CLIENT_ROLES: tuple[ClientRole, ...] = ("viewer", "operator", "admin")
AdminAction = Literal[
    "client.created",
    "client.disabled",
    "client.enabled",
    "user.invited",
    "user.role_changed",
    "user.disabled",
    "user.enabled",
    "user.password_reset",
    "user.removed",
    "credits.granted",
    "workflow.assigned",
]
# What follows "client-" in a group name: lowercase letters, digits and dashes.
CLIENT_SLUG = r"^[a-z0-9](?:[a-z0-9-]{0,48}[a-z0-9])?$"
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    ),
]


class ClientCreate(CamelModel):
    slug: str = Field(pattern=CLIENT_SLUG, description="The group is client-<slug>.")


class ClientSummary(CamelModel):
    account: str = Field(description="client-<slug>, the Keycloak group.")
    users: int
    active_users: int
    balance: int
    held: int
    low_balance: bool
    recent_runs: int
    recent_pages: int
    workflows: int
    in_keycloak: bool = Field(description="False: credits or workflows but no group any more.")


class ClientUser(CamelModel):
    id: str
    email: str
    first_name: str
    last_name: str
    role: ClientRole | None
    enabled: bool
    created_at: datetime | None


class LedgerEntry(CamelModel):
    id: str
    kind: CreditKind
    amount: int
    pending: bool
    run_id: str | None
    pages: int
    model_ms: int
    note: str
    actor: str
    created_at: datetime


class ClientWorkflow(CamelModel):
    id: str
    name: str
    status: str
    updated_at: datetime


class ClientDetail(CamelModel):
    summary: ClientSummary
    users: list[ClientUser]
    ledger: list[LedgerEntry]
    workflows: list[ClientWorkflow]


class UserInvite(CamelModel):
    email: Email
    first_name: Name = ""
    last_name: Name = ""
    role: ClientRole = "operator"


class UserChange(CamelModel):
    role: ClientRole | None = None
    enabled: bool | None = None


class TemporaryPassword(CamelModel):
    user: ClientUser
    temporary_password: str = Field(
        description="Shown once; Keycloak makes the user replace it at the first sign-in."
    )


class AdminGrant(CamelModel):
    amount: int = Field(ge=-1_000_000, le=1_000_000, description="Negative takes credits back.")
    note: Text = ""


class WorkflowAssign(CamelModel):
    account: str | None = Field(
        default=None,
        pattern=r"^client-[a-z0-9][a-z0-9-]*$",
        description="The client to give it to; None makes it shared again.",
    )


class SharedWorkflow(CamelModel):
    id: str
    name: str
    account: str | None
    status: str
    updated_at: datetime


class SpendAccount(CamelModel):
    account: str
    runs: int
    pages: int
    model_ms: int
    dollars: float


class Spend(CamelModel):
    since: datetime
    runs: int
    pages: int
    model_ms: int
    dollars: float = Field(description="Model time at AUDIT_GPU_DOLLARS_PER_HOUR (an estimate).")
    dollars_per_hour: float
    accounts: list[SpendAccount]


class AdminEventOut(CamelModel):
    id: str
    actor: str
    action: AdminAction
    account: str | None
    target: str
    detail: dict
    created_at: datetime


class AdminOverview(CamelModel):
    enabled: bool = Field(description="False: the Keycloak admin account is not configured.")
    low_balance_threshold: int
    clients: list[ClientSummary]
    spend: Spend
