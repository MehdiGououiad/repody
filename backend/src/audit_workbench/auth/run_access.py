"""Run access policy — single module for credential → principal/source resolution."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.auth.casbin_authorizer import get_authorizer
from audit_workbench.auth.dependencies import extract_bearer
from audit_workbench.auth.jwt_validator import JwtValidationError, principal_from_bearer
from audit_workbench.db.models import Workflow
from audit_workbench.services.api_keys import verify_api_key
from audit_workbench.services.run_enqueue_errors import (
    ForbiddenRunError,
    UnauthorizedRunError,
    WorkflowNotFoundError,
)
from audit_workbench.services.workflow import load_workflow
from audit_workbench.settings import Settings, get_settings

RunSource = str  # "test" | "api"


def resolve_owner_subject(
    authorization: str | None,
    *,
    settings: Settings | None = None,
) -> str | None:
    """Map bearer JWT to owner subject for upload binding; dev mode uses a fixed subject."""
    cfg = settings or get_settings()
    if not cfg.oidc_enabled:
        return "dev-local"
    token = extract_bearer(authorization)
    if not token:
        return None
    try:
        return principal_from_bearer(token, cfg).subject
    except JwtValidationError:
        return None


async def resolve_run_enqueue_source(
    session: AsyncSession,
    workflow_id: str,
    authorization: str | None,
    *,
    has_snapshot: bool = False,
    production_api_shape: bool = False,
) -> tuple[RunSource, Workflow]:
    """Infer test vs production API run from bearer credential and request shape."""
    settings = get_settings()
    token = extract_bearer(authorization)

    wf = await load_workflow(session, workflow_id)
    if not wf:
        raise WorkflowNotFoundError

    if token and wf.deployed_at and verify_api_key(token, wf.api_key):
        return "api", wf

    if token and settings.oidc_enabled:
        try:
            principal = principal_from_bearer(token, settings)
        except JwtValidationError as exc:
            raise UnauthorizedRunError(f"Unauthorized — {exc}") from exc

        if not principal.has_app_role():
            raise ForbiddenRunError("No application role assigned in Keycloak.")

        authorizer = get_authorizer()
        if not authorizer.authorize(principal, "run", "execute"):
            raise ForbiddenRunError("Forbidden — operator role required for test runs.")

        return "test", wf

    if token and not settings.oidc_enabled:
        raise UnauthorizedRunError("Invalid API key.")

    if settings.oidc_enabled:
        raise UnauthorizedRunError("Missing bearer token.")

    if production_api_shape or (wf.deployed_at and not has_snapshot):
        raise UnauthorizedRunError("Invalid API key.")

    return "test", wf
