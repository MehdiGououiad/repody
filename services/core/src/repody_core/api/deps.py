"""FastAPI dependencies for ``repody_core``."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from repody_common.ports import EntitlementProvider
from repody_core.app.ports import CoreStore, EventPublisher, PipelineDispatcher
from repody_core.infra import db
from repody_core.infra.auth import DEV_USER, CoreUser, InvalidTokenError, user_from_token
from repody_core.infra.entitlements import EnvEntitlementProvider
from repody_core.infra.queue import HatchetEventPublisher
from repody_core.infra.repository import SqlCoreStore
from repody_core.settings import get_settings

bearer = HTTPBearer(auto_error=False, description="Keycloak access token")


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session."""
    async with db.get_session_factory()() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_store(session: SessionDep) -> CoreStore:
    """Return the configured ``CoreStore`` implementation."""
    return SqlCoreStore(session)


StoreDep = Annotated[CoreStore, Depends(get_store)]


def get_publisher() -> EventPublisher:
    """Return the Hatchet durable event publisher."""
    return HatchetEventPublisher()


PublisherDep = Annotated[EventPublisher, Depends(get_publisher)]


def get_dispatcher() -> PipelineDispatcher:
    """Return the Hatchet durable pipeline dispatcher."""
    return HatchetEventPublisher()


DispatcherDep = Annotated[PipelineDispatcher, Depends(get_dispatcher)]


def get_entitlement_provider() -> EntitlementProvider:
    """Return the offline Ed25519 entitlement provider."""
    return EnvEntitlementProvider()


EntitlementDep = Annotated[EntitlementProvider, Depends(get_entitlement_provider)]


def optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    x_dev_user: Annotated[str | None, Header()] = None,
) -> CoreUser | None:
    """Resolve the caller; ``X-Dev-User`` is honored only when OIDC is disabled."""
    settings = get_settings()
    if not settings.oidc_enabled:
        if x_dev_user and x_dev_user.strip():
            return CoreUser(subject=x_dev_user.strip(), roles=DEV_USER.roles)
        return DEV_USER
    if credentials is None:
        return None
    try:
        return user_from_token(credentials.credentials)
    except InvalidTokenError:
        return None


OptionalUser = Annotated[CoreUser | None, Depends(optional_user)]


def require(permission: str):
    """Enforce an RBAC permission on the route."""

    def dependency(user: OptionalUser) -> CoreUser:
        if user is None:
            raise HTTPException(401, "Sign in to continue.")
        if not user.can(permission):
            raise HTTPException(403, f"Missing permission {permission}.")
        return user

    return Depends(dependency)
