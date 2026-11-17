"""The admin area (platform admins only): clients, their users, credits, workflows, spend and
the audit log. Every change is recorded (repody.app.admin)."""

from typing import Annotated

from fastapi import APIRouter, Path, Query

from repody.api.deps import SessionDep, require
from repody.app import admin
from repody.infra.auth import User
from repody.schemas.admin import (
    AdminEventOut,
    AdminGrant,
    AdminOverview,
    ClientCreate,
    ClientDetail,
    ClientSummary,
    ClientUser,
    SharedWorkflow,
    TemporaryPassword,
    UserChange,
    UserInvite,
    WorkflowAssign,
)
from repody.schemas.credits import Credits

router = APIRouter(prefix="/admin", tags=["admin"])

Admin = Annotated[User, require("clients:manage")]
Account = Annotated[str, Path(pattern=r"^client-[a-z0-9][a-z0-9-]*$", max_length=64)]
UserId = Annotated[str, Path(max_length=64)]


@router.get("")
async def overview(session: SessionDep, _admin: Admin) -> AdminOverview:
    """Every client with its users, balance and use, and this month's GPU spend."""
    return await admin.overview(session)


@router.post("/clients", status_code=201)
async def create_client(body: ClientCreate, session: SessionDep, user: Admin) -> ClientSummary:
    """A new client company: the Keycloak group client-<slug>."""
    return await admin.create_client(session, body.slug, user.subject)


@router.get("/clients/{account}")
async def client(account: Account, session: SessionDep, _admin: Admin) -> ClientDetail:
    return await admin.client_detail(session, account)


@router.post("/clients/{account}/disable", status_code=204)
async def disable_client(account: Account, session: SessionDep, user: Admin) -> None:
    """Disable every user of the client (nobody of it can sign in)."""
    await admin.set_client_enabled(session, account, False, user.subject)


@router.post("/clients/{account}/enable", status_code=204)
async def enable_client(account: Account, session: SessionDep, user: Admin) -> None:
    await admin.set_client_enabled(session, account, True, user.subject)


@router.post("/clients/{account}/users", status_code=201)
async def invite(
    account: Account, body: UserInvite, session: SessionDep, user: Admin
) -> TemporaryPassword:
    """A new user of the client, with a temporary password shown only in this answer."""
    return await admin.invite(session, account, body, user.subject)


@router.patch("/clients/{account}/users/{user_id}")
async def change_user(
    account: Account, user_id: UserId, body: UserChange, session: SessionDep, user: Admin
) -> ClientUser:
    return await admin.change_user(session, account, user_id, body, user.subject)


@router.post("/clients/{account}/users/{user_id}/password")
async def reset_password(
    account: Account, user_id: UserId, session: SessionDep, user: Admin
) -> TemporaryPassword:
    """A new temporary password, shown only in this answer."""
    return await admin.reset_password(session, account, user_id, user.subject)


@router.delete("/clients/{account}/users/{user_id}", status_code=204)
async def remove_user(account: Account, user_id: UserId, session: SessionDep, user: Admin) -> None:
    """Out of the client and disabled."""
    await admin.remove_user(session, account, user_id, user.subject)


@router.post("/clients/{account}/credits", status_code=201)
async def grant(account: Account, body: AdminGrant, session: SessionDep, user: Admin) -> Credits:
    return await admin.grant(session, account, body, user.subject)


@router.get("/workflows")
async def workflows(session: SessionDep, _admin: Admin) -> list[SharedWorkflow]:
    """Every workflow, with the client it belongs to (None: shared)."""
    return await admin.workflows(session)


@router.put("/workflows/{workflow_id}/account")
async def assign_workflow(
    workflow_id: Annotated[str, Path(max_length=64)],
    body: WorkflowAssign,
    session: SessionDep,
    user: Admin,
) -> SharedWorkflow:
    return await admin.assign_workflow(session, workflow_id, body.account, user.subject)


@router.get("/events")
async def events(
    session: SessionDep,
    _admin: Admin,
    account: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[AdminEventOut]:
    """The audit log, newest first."""
    return await admin.events(session, account=account, limit=limit)
