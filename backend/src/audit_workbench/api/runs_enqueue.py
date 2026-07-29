"""Map enqueue Result to HTTP responses."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.api.errors import raise_app_error
from audit_workbench.runtime.run.contracts import EnqueueRunRequest
from audit_workbench.schemas.workflow import RunCreatedResponse
from audit_workbench.app.run.enqueue import enqueue_run


async def enqueue_run_http(
    session: AsyncSession,
    req: EnqueueRunRequest,
) -> RunCreatedResponse:
    result = await enqueue_run(session, req)
    if result.is_ok:
        return result.unwrap()
    assert result.error is not None
    raise_app_error(result.error)
