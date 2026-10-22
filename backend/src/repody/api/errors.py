"""Translate application ``AppError`` / ``Result`` values into HTTP errors."""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

from repody.runtime.contracts.result import AppError, Result, http_status_for


def http_exception_for(error: AppError) -> HTTPException:
    """Build HTTPException from AppError (Retry-After + optional numeric cause)."""
    status = int(error.cause) if error.cause and error.cause.isdigit() else http_status_for(error)
    headers = None
    if error.retry_after_seconds is not None:
        headers = {"Retry-After": str(error.retry_after_seconds)}
    return HTTPException(status_code=status, detail=error.message, headers=headers)


def raise_app_error(error: AppError) -> NoReturn:
    raise http_exception_for(error)


def unwrap_or_raise[T](result: Result[T]) -> T:
    """Return the success value, or raise the matching HTTPException."""
    if result.error:
        raise_app_error(result.error)
    return result.unwrap()
