"""Authentication dependencies for admin UI and workflow API keys."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.deps import get_session
from audit_workbench.db.models import Run, Workflow
from audit_workbench.services.api_keys import verify_api_key
from audit_workbench.settings import get_settings


def extract_bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return token or None


def _admin_token_matches(provided: str | None) -> bool:
    settings = get_settings()
    expected = settings.admin_api_token
    if not provided or not expected:
        return False
    return secrets.compare_digest(provided, expected)


async def require_admin(
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Require a valid admin bearer token when auth is enabled."""
    settings = get_settings()
    if not settings.auth_enabled:
        return
    token = extract_bearer(authorization)
    if not _admin_token_matches(token):
        raise HTTPException(401, "Unauthorized — valid admin API token required.")


async def require_admin_or_workflow_run(
    run_id: str,
    authorization: Annotated[str | None, Header()] = None,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Allow admin token or the workflow API key that owns the run."""
    settings = get_settings()
    if not settings.auth_enabled:
        return

    token = extract_bearer(authorization)
    if _admin_token_matches(token):
        return

    run = await session.get(Run, run_id)
    if not run:
        raise HTTPException(404, "Run not found")

    wf = await session.get(Workflow, run.workflow_id)
    if wf and verify_api_key(token, wf.api_key):
        return

    raise HTTPException(401, "Unauthorized — admin token or workflow API key required.")


async def require_test_run_admin(
    mode: str | None = Query(None),
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    """Test-mode runs are UI-only and require admin when auth is enabled."""
    if mode != "test":
        return
    await require_admin(authorization)
