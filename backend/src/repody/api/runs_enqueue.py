"""Map enqueue Result to HTTP responses."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from repody.api.errors import raise_app_error
from repody.app.run.enqueue import enqueue_run
from repody.runtime.run.contracts import EnqueueRunRequest
from repody.schemas.workflow import RunCreatedResponse


async def enqueue_run_http(
    session: AsyncSession,
    req: EnqueueRunRequest,
) -> RunCreatedResponse:
    result = await enqueue_run(session, req)
    if result.is_ok:
        return result.unwrap()
    assert result.error is not None
    raise_app_error(result.error)
    return None
