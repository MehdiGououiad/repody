"""Request dependencies: a database session and the caller."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from repody import db
from repody.auth import DEV_USER, InvalidTokenError, Permission, User, user_from_token
from repody.settings import get_settings


async def get_session() -> AsyncIterator[AsyncSession]:
    async with db.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]

bearer = HTTPBearer(auto_error=False, description="Keycloak access token or workflow API key")
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]


def token_of(credentials: HTTPAuthorizationCredentials | None) -> str | None:
    return credentials.credentials if credentials else None


def optional_user(credentials: BearerDep) -> User | None:
    """The signed-in user, None without a valid token (always the dev user without OIDC)."""
    if not get_settings().oidc_enabled:
        return DEV_USER
    token = token_of(credentials)
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
