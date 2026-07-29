"""HTTP mapping for AppError — preferred raise path for AppError from routers."""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

from repody.runtime.contracts.result import AppError, http_status_for


def http_exception_for(error: AppError) -> HTTPException:
    """Build HTTPException from AppError (Retry-After + optional numeric cause)."""
    if error.cause and error.cause.isdigit():
        status = int(error.cause)
    else:
        status = http_status_for(error)
    headers = None
    if error.retry_after_seconds is not None:
        headers = {"Retry-After": str(error.retry_after_seconds)}
    return HTTPException(status_code=status, detail=error.message, headers=headers)


def raise_app_error(error: AppError) -> NoReturn:
    raise http_exception_for(error)
