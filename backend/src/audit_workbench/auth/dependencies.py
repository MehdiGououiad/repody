"""FastAPI authentication and Casbin authorization dependencies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.auth.casbin_authorizer import get_authorizer
from audit_workbench.auth.jwt_validator import JwtValidationError, principal_from_bearer
from audit_workbench.auth.principal import Principal
from audit_workbench.db.models import Run, Workflow
from audit_workbench.services.api_keys import verify_api_key
from audit_workbench.settings import get_settings


def extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, separator, token = authorization.strip().partition(" ")
    if not separator or scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _dev_principal() -> Principal:
    return Principal(subject="dev-local", roles=("platform_admin",), email="dev@local")


async def get_current_principal(
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    settings = get_settings()
    if not settings.oidc_enabled:
        return _dev_principal()

    token = extract_bearer(authorization)
    try:
        principal = principal_from_bearer(token, settings)
    except JwtValidationError as exc:
        raise HTTPException(401, f"Unauthorized — {exc}") from exc

    if not principal.has_app_role():
        raise HTTPException(403, "No application role assigned in Keycloak.")
    return principal


async def require_management_access(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    if not principal.has_app_role():
        raise HTTPException(403, "Application role required.")
    return principal


def require_permission(resource: str, action: str) -> Callable:
    async def _dependency(
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        authorizer = get_authorizer()
        if not authorizer.authorize(principal, resource, action):
            raise HTTPException(
                403,
                f"Forbidden — missing permission {resource}:{action}.",
            )
        return principal

    return _dependency


# Back-compat alias — prefer require_permission per route.
require_admin = require_management_access


async def require_admin_or_workflow_run(
    run_id: str,
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> None:
    settings = get_settings()
    if not settings.oidc_enabled:
        return

    token = extract_bearer(authorization)
    if not token:
        raise HTTPException(401, "Unauthorized — sign in or provide the workflow API key.")

    try:
        principal = principal_from_bearer(token, settings)
        if principal.has_app_role():
            authorizer = get_authorizer()
            if authorizer.authorize(principal, "run", "read"):
                return
    except JwtValidationError:
        pass

    run = await session.get(Run, run_id)
    if run:
        wf = await session.get(Workflow, run.workflow_id)
        if wf and verify_api_key(token, wf.api_key):
            return

    raise HTTPException(401, "Unauthorized — sign in or provide the workflow API key.")


async def require_run_create_access(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Require a bearer token; test vs API source is resolved in enqueue_run."""
    settings = get_settings()
    if not settings.oidc_enabled:
        return
    if not extract_bearer(authorization):
        raise HTTPException(401, "Missing bearer token.")
