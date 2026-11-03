"""Translate ``AppError`` into HTTP responses (registered as a FastAPI exception handler)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from repody.runtime.contracts.result import AppError, http_status_for


def status_for(error: AppError) -> int:
    """HTTP status for an AppError; a numeric ``cause`` (e.g. "413") overrides the code map."""
    return int(error.cause) if error.cause and error.cause.isdigit() else http_status_for(error)


async def app_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    headers = None
    if exc.retry_after_seconds is not None:
        headers = {"Retry-After": str(exc.retry_after_seconds)}
    return JSONResponse({"detail": exc.message}, status_code=status_for(exc), headers=headers)
