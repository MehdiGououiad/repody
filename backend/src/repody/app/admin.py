"""The admin area for platform admins: client companies (Keycloak groups ``client-<slug>``), their
users, credits, workflows handed to a client, GPU spend, and the audit log of every change.

Keycloak stays the source of truth for users, passwords and groups; Repody reaches it as the
``repody-admin`` service account (repody.infra.keycloak_admin). Only users of a client group are
ever changed here, and only to a client role (viewer, operator, admin): a platform admin cannot be
edited, nor made, from the admin area.
"""

import asyncio
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app import credits
from repody.app.errors import AppError
from repody.infra import keycloak_admin
from repody.infra.auth import CLIENT_GROUP_PREFIX
from repody.infra.keycloak_admin import KcUser, KeycloakAdmin
from repody.infra.models import AdminEvent, CreditEntry, Workflow, new_id
from repody.schemas.admin import (
    CLIENT_ROLES,
    AdminAction,
    AdminEventOut,
    AdminGrant,
    AdminOverview,
    ClientDetail,
    ClientRole,
    ClientSummary,
    ClientUser,
    ClientWorkflow,
    LedgerEntry,
    SharedWorkflow,
    Spend,
    SpendAccount,
    TemporaryPassword,
    UserChange,
    UserInvite,
)
from repody.schemas.credits import AccountUsage, Credits
from repody.settings import get_settings

log = structlog.get_logger(__name__)

MANAGED_ROLES = frozenset(CLIENT_ROLES)
PROTECTED_ROLES = frozenset({"platform_admin"})
LEDGER_ROWS = 100
NOT_CONFIGURED = (
    "The admin area needs Keycloak's repody-admin account (AUDIT_KEYCLOAK_ADMIN_CLIENT_SECRET):"
    " see deploy/ENV.md, Admin area."
)


def keycloak_admin_or_503() -> KeycloakAdmin:
    if not keycloak_admin.enabled():
        raise AppError(503, NOT_CONFIGURED)
    return keycloak_admin.keycloak_admin()


def _temporary_password() -> str:
    # 16 URL-safe characters: over the realm's minimum length, and never the username.
    return secrets.token_urlsafe(12)


async def record(
    session: AsyncSession,
    actor: str,
    action: AdminAction,
    account: str | None,
    target: str = "",
    **detail: Any,
) -> None:
    session.add(
        AdminEvent(
            id=new_id("adm"),
            actor=actor,
            action=action,
            account_id=account,
            target=target,
            detail=detail,
        )
    )
    log.info("admin_action", actor=actor, action=action, account=account, target=target, **detail)


def _role(user: KcUser) -> ClientRole | None:
    for role in reversed(CLIENT_ROLES):  # the strongest one counts
        if role in user.realm_roles:
            return role
    return None


def _client_user(user: KcUser) -> ClientUser:
    return ClientUser(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=_role(user),
        enabled=user.enabled,
        created_at=datetime.fromtimestamp(user.created_ms / 1000, UTC) if user.created_ms else None,
    )


# --- Overview ---


async def _usage(
    session: AsyncSession, since: datetime, account: str | None = None
) -> dict[str, AccountUsage]:
    """Per account: its balance now, and its settled runs since ``since`` (repody.app.credits)."""
    report = await credits.usage(session, account=account, since=since)
    return {u.account: u for u in report.accounts}


def _thirty_days_ago() -> datetime:
    return datetime.now(UTC) - timedelta(days=30)


async def _workflow_counts(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(
        select(Workflow.account_id, func.count())
        .where(Workflow.status != "archived", Workflow.account_id.like(f"{CLIENT_GROUP_PREFIX}%"))
        .group_by(Workflow.account_id)
    )
    return {acc: count for acc, count in rows if acc}


def _summary(
    account: str,
    *,
    users: int,
    active: int,
    usage: AccountUsage | None,
    workflows: int,
    in_keycloak: bool,
) -> ClientSummary:
    balance = usage.balance if usage else 0
    return ClientSummary(
        account=account,
        users=users,
        active_users=active,
        balance=balance,
        held=usage.held if usage else 0,
        low_balance=balance < get_settings().credit_low_balance,
        recent_runs=usage.runs if usage else 0,
        recent_pages=usage.pages if usage else 0,
        workflows=workflows,
        in_keycloak=in_keycloak,
    )


async def spend(session: AsyncSession, since: datetime) -> Spend:
    rate = get_settings().gpu_dollars_per_hour

    def dollars(ms: int) -> float:
        return round(ms / 3_600_000 * rate, 2)

    used = [u for u in (await _usage(session, since)).values() if u.runs]
    accounts = [
        SpendAccount(
            account=u.account,
            runs=u.runs,
            pages=u.pages,
            model_ms=u.model_ms,
            dollars=dollars(u.model_ms),
        )
        for u in sorted(used, key=lambda u: -u.model_ms)
    ]
    total_ms = sum(a.model_ms for a in accounts)
    return Spend(
        since=since,
        runs=sum(a.runs for a in accounts),
        pages=sum(a.pages for a in accounts),
        model_ms=total_ms,
        dollars=dollars(total_ms),
        dollars_per_hour=rate,
        accounts=accounts,
    )


def month_start() -> datetime:
    return datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def overview(session: AsyncSession) -> AdminOverview:
    """Every client: its Keycloak group, users, balance and recent use, and this month's spend.
    Accounts with credits or workflows but no group any more are listed too."""
    groups: dict[str, int] = {}
    active: dict[str, int] = {}
    if keycloak_admin.enabled():
        kc = keycloak_admin.keycloak_admin()
        found = await kc.groups(CLIENT_GROUP_PREFIX)
        members = await asyncio.gather(*(kc.members(g.id, roles=False) for g in found))
        for group, users in zip(found, members, strict=True):
            groups[group.name] = len(users)
            active[group.name] = sum(u.enabled for u in users)
    usage = await _usage(session, _thirty_days_ago())
    workflows = await _workflow_counts(session)
    known = {acc for acc in (*groups, *usage, *workflows) if acc.startswith(CLIENT_GROUP_PREFIX)}
    return AdminOverview(
        enabled=keycloak_admin.enabled(),
        low_balance_threshold=get_settings().credit_low_balance,
        clients=[
            _summary(
                acc,
                users=groups.get(acc, 0),
                active=active.get(acc, 0),
                usage=usage.get(acc),
                workflows=workflows.get(acc, 0),
                in_keycloak=acc in groups,
            )
            for acc in sorted(known)
        ],
        spend=await spend(session, month_start()),
    )


# --- Clients ---


async def create_client(session: AsyncSession, slug: str, actor: str) -> ClientSummary:
    account = f"{CLIENT_GROUP_PREFIX}{slug}"
    kc = keycloak_admin_or_503()
    if await kc.group(account) is not None:
        raise AppError(409, f"{account} already exists.")
    await kc.create_group(account)
    await record(session, actor, "client.created", account)
    await session.commit()
    return _summary(
        account,
        users=0,
        active=0,
        usage=(await _usage(session, _thirty_days_ago(), account)).get(account),
        workflows=0,
        in_keycloak=True,
    )


async def group_id(kc: KeycloakAdmin, account: str) -> str:
    group = await kc.group(account)
    if group is None:
        raise AppError(404, f"No client {account}.")
    return group.id


async def client_detail(session: AsyncSession, account: str) -> ClientDetail:
    kc = keycloak_admin_or_503()
    group = await kc.group(account)
    users = [_client_user(u) for u in await kc.members(group.id)] if group else []
    if group is None and not await session.scalar(
        select(func.count()).where(CreditEntry.account_id == account)
    ):
        raise AppError(404, f"No client {account}.")
    ledger = await session.scalars(
        select(CreditEntry)
        .where(CreditEntry.account_id == account)
        .order_by(CreditEntry.created_at.desc())
        .limit(LEDGER_ROWS)
    )
    workflows = (
        await session.scalars(
            select(Workflow)
            .where(Workflow.account_id == account, Workflow.status != "archived")
            .order_by(Workflow.updated_at.desc())
        )
    ).all()
    return ClientDetail(
        summary=_summary(
            account,
            users=len(users),
            active=sum(u.enabled for u in users),
            usage=(await _usage(session, _thirty_days_ago(), account)).get(account),
            workflows=len(workflows),
            in_keycloak=group is not None,
        ),
        users=users,
        ledger=[
            LedgerEntry(
                id=e.id,
                kind=e.kind,
                amount=e.amount,
                pending=e.pending,
                run_id=e.run_id,
                pages=e.pages,
                model_ms=e.model_ms,
                note=e.note,
                actor=e.actor,
                created_at=e.created_at,
            )
            for e in ledger
        ],
        workflows=[
            ClientWorkflow(id=w.id, name=w.name, status=w.status, updated_at=w.updated_at)
            for w in workflows
        ],
    )


async def set_client_enabled(
    session: AsyncSession, account: str, enabled: bool, actor: str
) -> None:
    """Disable (or enable again) every user of the client: they cannot sign in meanwhile."""
    kc = keycloak_admin_or_503()
    for user in await kc.members(await group_id(kc, account)):
        if not user.realm_roles & PROTECTED_ROLES:
            await kc.set_enabled(user.id, enabled)
    await record(session, actor, "client.enabled" if enabled else "client.disabled", account)
    await session.commit()


# --- Users ---


async def invite(
    session: AsyncSession, account: str, body: UserInvite, actor: str
) -> TemporaryPassword:
    """A new user in the client, with a temporary password shown once (Keycloak makes them
    replace it at the first sign-in)."""
    kc = keycloak_admin_or_503()
    gid = await group_id(kc, account)
    user_id = await kc.create_user(
        email=body.email, first_name=body.first_name, last_name=body.last_name
    )
    password = _temporary_password()
    await kc.set_temporary_password(user_id, password)
    await kc.set_role(user_id, body.role, MANAGED_ROLES)
    await kc.join(user_id, gid)
    await record(session, actor, "user.invited", account, body.email, role=body.role)
    await session.commit()
    return TemporaryPassword(user=_client_user(await kc.user(user_id)), temporary_password=password)


async def _member(kc: KeycloakAdmin, account: str, user_id: str) -> KcUser:
    """The user, if they belong to this client and are not a platform admin."""
    groups = {g.name for g in await kc.user_groups(user_id)}
    if account not in groups:
        raise AppError(404, "No such user in this client.")
    user = await kc.user(user_id)
    if user.realm_roles & PROTECTED_ROLES:
        raise AppError(403, "Platform admins are managed in Keycloak, not here.")
    return user


async def change_user(
    session: AsyncSession, account: str, user_id: str, body: UserChange, actor: str
) -> ClientUser:
    kc = keycloak_admin_or_503()
    user = await _member(kc, account, user_id)
    if body.role is not None and body.role != _role(user):
        await kc.set_role(user_id, body.role, MANAGED_ROLES)
        await record(session, actor, "user.role_changed", account, user.email, role=body.role)
    if body.enabled is not None and body.enabled != user.enabled:
        await kc.set_enabled(user_id, body.enabled)
        await record(
            session, actor, "user.enabled" if body.enabled else "user.disabled", account, user.email
        )
    await session.commit()
    return _client_user(await kc.user(user_id))


async def reset_password(
    session: AsyncSession, account: str, user_id: str, actor: str
) -> TemporaryPassword:
    kc = keycloak_admin_or_503()
    user = await _member(kc, account, user_id)
    password = _temporary_password()
    await kc.set_temporary_password(user_id, password)
    await record(session, actor, "user.password_reset", account, user.email)
    await session.commit()
    return TemporaryPassword(user=_client_user(user), temporary_password=password)


async def remove_user(session: AsyncSession, account: str, user_id: str, actor: str) -> None:
    """Disabled, then out of the client: they keep no access (Keycloak keeps the account, for the
    record; delete it there if needed). Disabled first: if leaving fails, they are a disabled
    member, never an enabled user outside every client."""
    kc = keycloak_admin_or_503()
    user = await _member(kc, account, user_id)
    await kc.set_enabled(user_id, False)
    await kc.leave(user_id, await group_id(kc, account))
    await record(session, actor, "user.removed", account, user.email)
    await session.commit()


# --- Credits and workflows ---


async def grant(session: AsyncSession, account: str, body: AdminGrant, actor: str) -> Credits:
    balance = await credits.grant(session, account, body.amount, body.note, actor)
    await record(session, actor, "credits.granted", account, amount=body.amount, note=body.note)
    await session.commit()
    return balance


async def workflows(session: AsyncSession) -> list[SharedWorkflow]:
    rows = await session.scalars(
        select(Workflow).where(Workflow.status != "archived").order_by(Workflow.updated_at.desc())
    )
    return [
        SharedWorkflow(
            id=w.id, name=w.name, account=w.account_id, status=w.status, updated_at=w.updated_at
        )
        for w in rows
    ]


async def assign_workflow(
    session: AsyncSession, workflow_id: str, account: str | None, actor: str
) -> SharedWorkflow:
    """Give a workflow to a client (its users then edit and run it), or share it again (None).
    Its past runs stay with the account that paid for them."""
    wf = await session.get(Workflow, workflow_id)
    if wf is None or wf.status == "archived":
        raise AppError(404, "Workflow not found.")
    if account is not None and keycloak_admin.enabled():
        await group_id(keycloak_admin_or_503(), account)
    previous = wf.account_id
    wf.account_id = account
    await record(
        session, actor, "workflow.assigned", account, wf.id, previous=previous, name=wf.name
    )
    await session.commit()
    await session.refresh(wf)
    return SharedWorkflow(
        id=wf.id, name=wf.name, account=wf.account_id, status=wf.status, updated_at=wf.updated_at
    )


# --- Audit log ---


async def events(
    session: AsyncSession, *, account: str | None = None, limit: int = 200
) -> list[AdminEventOut]:
    query = select(AdminEvent).order_by(AdminEvent.created_at.desc()).limit(limit)
    if account:
        query = query.where(AdminEvent.account_id == account)
    return [
        AdminEventOut(
            id=e.id,
            actor=e.actor,
            action=e.action,
            account=e.account_id,
            target=e.target,
            detail=e.detail,
            created_at=e.created_at,
        )
        for e in await session.scalars(query)
    ]
