"""Request dependencies: a database session, the bearer token and the caller."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra import db
from repody.infra.auth import DEV_USER, InvalidTokenError, Permission, User, user_from_token
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


def optional_user(token: TokenDep) -> User | None:
    """The signed-in user, None without a valid token (always the dev user without OIDC)."""
    if not get_settings().oidc_enabled:
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
            raise HTTPException(403, f"Missing permission {permission}.")
        return user

    return Depends(dependency)
