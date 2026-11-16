"""Access requests: prospects ask on the site, a platform admin approves or declines.

Submitting is public: it needs a Turnstile token (when AUDIT_TURNSTILE_SECRET is set), and one
network sends at most AUDIT_ACCESS_REQUESTS_PER_HOUR (by a hash of its address, never the address
itself). A second request from an email still waiting is merged into the first. Approving creates
the client (or reuses it), invites the person with a one-time password and gives starting credits,
all through the admin area's use cases, so the audit log records each step.
"""

import hashlib
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from repody.app import admin
from repody.app.errors import AppError
from repody.infra import turnstile
from repody.infra.auth import CLIENT_GROUP_PREFIX
from repody.infra.models import AccessRequest, CreditEntry, new_id
from repody.schemas.access import (
    AccessApprove,
    AccessApproved,
    AccessDecline,
    AccessRequestIn,
    AccessRequestOut,
    AccessStatus,
)
from repody.schemas.admin import AdminGrant, ClientRole, TemporaryPassword, UserInvite
from repody.settings import get_settings

log = structlog.get_logger(__name__)


def _ip_hash(ip: str | None) -> str:
    return hashlib.sha256(ip.encode()).hexdigest() if ip else ""


def _out(r: AccessRequest) -> AccessRequestOut:
    return AccessRequestOut(
        id=r.id,
        name=r.name,
        email=r.email,
        company=r.company,
        sector=r.sector,
        message=r.message,
        locale=r.locale,
        status=r.status,
        note=r.note,
        account=r.account_id,
        decided_by=r.decided_by,
        created_at=r.created_at,
        decided_at=r.decided_at,
    )


async def submit(session: AsyncSession, body: AccessRequestIn, ip: str | None) -> None:
    ip_hash = _ip_hash(ip)
    if ip_hash:
        recent = await session.scalar(
            select(func.count()).where(
                AccessRequest.ip_hash == ip_hash,
                AccessRequest.created_at >= datetime.now(UTC) - timedelta(hours=1),
            )
        )
        if (recent or 0) >= get_settings().access_requests_per_hour:
            log.warning("access_request_rate_limited")
            raise AppError(
                429, "Too many requests from this network; try again later.", retry_after=3600
            )
    if not await turnstile.verify(body.turnstile_token, ip):
        raise AppError(400, "The anti-robot check failed; reload the page and try again.")
    waiting = await session.scalar(
        select(AccessRequest).where(
            AccessRequest.email == body.email, AccessRequest.status == "new"
        )
    )
    if waiting is not None:
        waiting.message = "\n\n".join(m for m in (waiting.message, body.message) if m)[:8000]
        await session.commit()
        log.info("access_request_merged", request_id=waiting.id)
        return
    request = AccessRequest(
        id=new_id("req"),
        name=body.name,
        email=body.email,
        company=body.company,
        sector=body.sector,
        message=body.message,
        locale=body.locale,
        consent_at=datetime.now(UTC),
        ip_hash=ip_hash,
    )
    session.add(request)
    await session.commit()
    log.info("access_requested", request_id=request.id, company=body.company)


async def requests(
    session: AsyncSession, *, status: AccessStatus | None = None, limit: int = 200
) -> list[AccessRequestOut]:
    query = select(AccessRequest).order_by(AccessRequest.created_at.desc()).limit(limit)
    if status:
        query = query.where(AccessRequest.status == status)
    return [_out(r) for r in await session.scalars(query)]


async def _pending(session: AsyncSession, request_id: str) -> AccessRequest:
    request = await session.get(AccessRequest, request_id)
    if request is None:
        raise AppError(404, "Request not found.")
    if request.status != "new":
        raise AppError(409, f"The request is already {request.status}.")
    return request


async def _person(
    session: AsyncSession, request: AccessRequest, account: str, role: ClientRole, actor: str
) -> TemporaryPassword:
    """The request's person in ``account``, with a temporary password to send them: invited when
    new; joined when Keycloak already knows them but they belong to no client; and when a retry
    finds them already in it (an approval that stopped halfway), given a fresh password."""
    kc = admin.keycloak_admin_or_503()
    existing = await admin.call(kc.find_user(request.email))
    if existing is None:
        first, _, last = request.name.partition(" ")
        invite = UserInvite(email=request.email, first_name=first, last_name=last, role=role)
        return await admin.invite(session, account, invite, actor)
    if existing.realm_roles & admin.PROTECTED_ROLES:
        raise AppError(409, f"{request.email} is a platform admin: approve with another email.")
    clients = {
        g.name
        for g in await admin.call(kc.user_groups(existing.id))
        if g.name.startswith(CLIENT_GROUP_PREFIX)
    }
    if clients - {account}:
        raise AppError(409, f"{request.email} already belongs to {', '.join(sorted(clients))}.")
    if account not in clients:
        await admin.call(kc.join(existing.id, await admin.group_id(kc, account)))
        await admin.call(kc.set_role(existing.id, role, admin.MANAGED_ROLES))
        await admin.call(kc.set_enabled(existing.id, True))
        await admin.record(session, actor, "user.invited", account, request.email, role=role)
        await session.commit()
    return await admin.reset_password(session, account, existing.id, actor)


async def approve(
    session: AsyncSession, request_id: str, body: AccessApprove, actor: str
) -> AccessApproved:
    """Safe to retry: each step checks what an earlier, interrupted approval already did."""
    request = await _pending(session, request_id)
    account = f"{CLIENT_GROUP_PREFIX}{body.slug}"
    kc = admin.keycloak_admin_or_503()
    if await admin.call(kc.group(account)) is None:
        await admin.create_client(session, body.slug, actor)
    invited = await _person(session, request, account, body.role, actor)
    note = f"Access request {request.id}"
    already_granted = await session.scalar(
        select(func.count()).where(
            CreditEntry.account_id == account, CreditEntry.kind == "grant", CreditEntry.note == note
        )
    )
    if body.credits and not already_granted:
        await admin.grant(session, account, AdminGrant(amount=body.credits, note=note), actor)
    request.status, request.account_id = "approved", account
    request.decided_by, request.decided_at = actor, datetime.now(UTC)
    await admin.record(
        session, actor, "request.approved", account, request.email, request=request.id
    )
    await session.commit()
    return AccessApproved(request=_out(request), invited=invited)


async def decline(
    session: AsyncSession, request_id: str, body: AccessDecline, actor: str
) -> AccessRequestOut:
    request = await _pending(session, request_id)
    request.status, request.note = "declined", body.note
    request.decided_by, request.decided_at = actor, datetime.now(UTC)
    await admin.record(session, actor, "request.declined", None, request.email, request=request.id)
    await session.commit()
    return _out(request)


async def purge_declined(session: AsyncSession) -> int:
    """Delete declined requests past AUDIT_ACCESS_REQUEST_RETENTION_DAYS. The caller commits."""
    days = get_settings().access_request_retention_days
    before = datetime.now(UTC) - timedelta(days=days)
    deleted = await session.scalars(
        delete(AccessRequest)
        .where(AccessRequest.status == "declined", AccessRequest.decided_at < before)
        .returning(AccessRequest.id)
    )
    return len(deleted.all())
