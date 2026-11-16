"""Access requests: the site's public form, and the admin area's list, approve and decline."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, Request

from repody.api.deps import SessionDep, require
from repody.app import access
from repody.infra.auth import User
from repody.schemas.access import (
    AccessApprove,
    AccessApproved,
    AccessDecline,
    AccessRequestIn,
    AccessRequestOut,
    AccessStatus,
)
from repody.settings import get_settings

router = APIRouter(tags=["access"])

Admin = Annotated[User, require("clients:manage")]
RequestId = Annotated[str, Path(max_length=64)]


def _client_ip(request: Request) -> str | None:
    """The visitor's address: Cloudflare's header (the tunnel), else the connection's."""
    return request.headers.get("cf-connecting-ip") or (
        request.client.host if request.client else None
    )


@router.post(
    "/access-requests",
    status_code=202,
    responses={
        400: {"description": "The anti-robot check failed."},
        404: {"description": "This installation takes no access requests."},
        429: {"description": "Too many requests from this network."},
    },
)
async def request_access(body: AccessRequestIn, request: Request, session: SessionDep) -> None:
    """Public: a prospect asks for an account (the site's form). 404 when this installation
    takes no requests (AUDIT_ACCESS_REQUESTS_ENABLED), 429 past the hourly limit per network, 400
    when the anti-robot check fails."""
    if not get_settings().access_requests_enabled:
        raise HTTPException(404, "Not Found")
    await access.submit(session, body, _client_ip(request))


@router.get("/admin/requests")
async def list_requests(
    session: SessionDep,
    _admin: Admin,
    status: Annotated[AccessStatus | None, Query()] = None,
) -> list[AccessRequestOut]:
    return await access.requests(session, status=status)


@router.post("/admin/requests/{request_id}/approve")
async def approve(
    request_id: RequestId, body: AccessApprove, session: SessionDep, user: Admin
) -> AccessApproved:
    """Create (or reuse) the client, invite the person (temporary password in this answer only)
    and give starting credits."""
    return await access.approve(session, request_id, body, user.subject)


@router.post("/admin/requests/{request_id}/decline")
async def decline(
    request_id: RequestId, body: AccessDecline, session: SessionDep, user: Admin
) -> AccessRequestOut:
    return await access.decline(session, request_id, body, user.subject)
