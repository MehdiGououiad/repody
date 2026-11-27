"""FastAPI dependency injection for ``repody_fraud``."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from repody_fraud.app.ports import ArtifactStorage, FraudStore
from repody_fraud.app.service import FraudService
from repody_fraud.infra import db
from repody_fraud.infra.auth import DEV_USER, FraudUser, InvalidTokenError, user_from_token
from repody_fraud.infra.explainer import build_explainer
from repody_fraud.infra.repository import SqlFraudStore
from repody_fraud.infra.storage import get_s3_storage
from repody_fraud.settings import get_settings

bearer = HTTPBearer(auto_error=False, description="Keycloak access token")


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    async with db.get_session_factory()() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_store(session: SessionDep) -> FraudStore:
    """Return configured ``FraudStore`` implementation."""
    return SqlFraudStore(session)


StoreDep = Annotated[FraudStore, Depends(get_store)]


def get_storage() -> ArtifactStorage:
    """Return configured ``ArtifactStorage`` implementation."""
    return get_s3_storage()


StorageDep = Annotated[ArtifactStorage, Depends(get_storage)]


def get_service(store: StoreDep, storage: StorageDep) -> FraudService:
    """Build ``FraudService`` wired with Postgres, S3, and optional explainer."""
    return FraudService(store=store, storage=storage, explainer=build_explainer())


ServiceDep = Annotated[FraudService, Depends(get_service)]


def optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    x_dev_user: Annotated[str | None, Header()] = None,
) -> FraudUser | None:
    """Resolve the caller; ``X-Dev-User`` is honored only when OIDC is disabled."""
    settings = get_settings()
    if not settings.oidc_enabled:
        if x_dev_user and x_dev_user.strip():
            return FraudUser(subject=x_dev_user.strip(), roles=DEV_USER.roles)
        return DEV_USER
    if credentials is None:
        return None
    try:
        return user_from_token(credentials.credentials)
    except InvalidTokenError:
        return None


OptionalUser = Annotated[FraudUser | None, Depends(optional_user)]


def require(permission: str):
    """Enforce RBAC permission on a Fraud Shield route."""

    def dependency(user: OptionalUser) -> FraudUser:
        if user is None:
            raise HTTPException(401, "Sign in to continue.")
        if not user.can(permission):
            raise HTTPException(403, f"Missing permission {permission}.")
        return user

    return Depends(dependency)
