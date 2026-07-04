"""Map run enqueue domain errors to HTTP responses."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.schemas.workflow import RunCreatedResponse
from audit_workbench.services.admission import QueueCapacityExceeded
from audit_workbench.services.rate_limit import RunRateLimitExceeded
from audit_workbench.services.run_enqueue import EnqueueRunRequest, enqueue_run
from audit_workbench.services.run_enqueue_errors import (
    ForbiddenRunError,
    RunEnqueueError,
    UnauthorizedRunError,
    WorkflowNotDeployedError,
    WorkflowNotFoundError,
)


async def enqueue_run_http(
    session: AsyncSession,
    req: EnqueueRunRequest,
) -> RunCreatedResponse:
    try:
        return await enqueue_run(session, req)
    except WorkflowNotFoundError as exc:
        raise HTTPException(404, "Workflow not found") from exc
    except UnauthorizedRunError as exc:
        raise HTTPException(401, exc.message) from exc
    except ForbiddenRunError as exc:
        raise HTTPException(403, exc.message) from exc
    except WorkflowNotDeployedError as exc:
        raise HTTPException(409, "Workflow is not deployed.") from exc
    except RunRateLimitExceeded as exc:
        raise HTTPException(429, str(exc)) from exc
    except RunEnqueueError as exc:
        raise HTTPException(429, str(exc)) from exc
    except QueueCapacityExceeded as exc:
        raise HTTPException(
            503,
            str(exc),
            headers={"Retry-After": str(exc.retry_after_seconds)},
        ) from exc
