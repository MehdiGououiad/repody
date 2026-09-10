"""Run access policy — credential → principal/source as Result."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from repody.app.api_keys import verify_api_key
from repody.app.workflow.repository import load_workflow
from repody.infra.auth.casbin_authorizer import authorize
from repody.infra.auth.dependencies import extract_bearer
from repody.infra.auth.jwt_validator import JwtValidationError, principal_from_bearer
from repody.infra.db.models import Workflow
from repody.runtime.contracts.result import AppError, ErrorCode, Result
from repody.settings import Settings, get_settings

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
) -> Result[tuple[RunSource, Workflow]]:
    """Infer test vs production API run from bearer credential and request shape."""
    settings = get_settings()
    token = extract_bearer(authorization)

    wf = await load_workflow(session, workflow_id)
    if not wf:
        return Result.fail(AppError(code=ErrorCode.NOT_FOUND, message="Workflow not found"))

    if token and wf.deployed_at and verify_api_key(token, wf.api_key):
        return Result.ok(("api", wf))

    if token and settings.oidc_enabled:
        try:
            principal = principal_from_bearer(token, settings)
        except JwtValidationError as exc:
            return Result.fail(
                AppError(code=ErrorCode.UNAUTHORIZED, message=f"Unauthorized — {exc}")
            )

        if not principal.has_app_role():
            return Result.fail(
                AppError(
                    code=ErrorCode.FORBIDDEN,
                    message="No application role assigned in Keycloak.",
                )
            )

        if not authorize(principal, "run", "execute"):
            return Result.fail(
                AppError(
                    code=ErrorCode.FORBIDDEN,
                    message="Forbidden — operator role required for test runs.",
                )
            )

        return Result.ok(("test", wf))

    if token and not settings.oidc_enabled:
        return Result.fail(AppError(code=ErrorCode.UNAUTHORIZED, message="Invalid API key."))

    if settings.oidc_enabled:
        return Result.fail(AppError(code=ErrorCode.UNAUTHORIZED, message="Missing bearer token."))

    if production_api_shape or (wf.deployed_at and not has_snapshot):
        return Result.fail(AppError(code=ErrorCode.UNAUTHORIZED, message="Invalid API key."))

    return Result.ok(("test", wf))
