"""Request dependencies: a database session, the bearer token and the caller."""

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra import db
from repody.infra.auth import (
    DEMO_VISITOR_ROLE,
    DEV_USER,
    InvalidTokenError,
    Permission,
    User,
    user_from_token,
)
from repody.settings import get_settings


async def get_session() -> AsyncIterator[AsyncSession]:
    async with db.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

bearer = HTTPBearer(auto_error=False, description="Keycloak access token or workflow API key")


def bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> str | None:
    """The request's bearer token: a Keycloak access token or a workflow API key."""
    return credentials.credentials if credentials else None


TokenDep = Annotated[str | None, Depends(bearer_token)]


VISITOR_HEADER = "X-Repody-Visitor"
CREDITS = "The playground does not run documents. Contact us for credits to continue."


def _visitor(header: str | None) -> User | None:
    """The playground visitor the web app names (a random UUID kept in its cookie)."""
    try:
        visitor = uuid.UUID(header or "")
    except ValueError:
        return None
    return User(subject=f"visitor-{visitor.hex}", roles=frozenset({DEMO_VISITOR_ROLE}))


def optional_user(
    token: TokenDep,
    visitor: Annotated[str | None, Header(alias=VISITOR_HEADER, include_in_schema=False)] = None,
) -> User | None:
    """The caller: in demo mode the anonymous visitor (no visitor header: nobody); else the
    signed-in user, None without a valid token (always the dev user without OIDC)."""
    settings = get_settings()
    if settings.demo_mode:
        return _visitor(visitor)
    if not settings.oidc_enabled:
        return DEV_USER
    if token is None:
        return None
    try:
        return user_from_token(token)
    except InvalidTokenError:
        return None


OptionalUser = Annotated[User | None, Depends(optional_user)]


def require(permission: Permission):
    def dependency(user: OptionalUser) -> User:
        if user is None:
            raise HTTPException(401, "Sign in to continue.")
        if not user.can(permission):
            if user.visitor:  # a playground visitor reaching for what costs model time
                raise HTTPException(402, CREDITS)
            raise HTTPException(403, f"Missing permission {permission}.")
        return user

    return Depends(dependency)


def visitor_scope(user: OptionalUser) -> str | None:
    """Whose workflows the caller sees: a playground visitor's own (and the examples); None
    outside demo mode, where everyone sees every workflow."""
    return user.visitor if user else None


VisitorScope = Annotated[str | None, Depends(visitor_scope)]
