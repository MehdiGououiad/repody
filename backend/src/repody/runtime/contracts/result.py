"""AppError - the one application exception, mapped to HTTP status at the API edge."""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    BAD_REQUEST = "bad_request"
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    EXTRACTION = "extraction"
    RULES = "rules"
    INFRA = "infra"
    SKIPPED = "skipped"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    RATE_LIMIT = "rate_limit"
    CAPACITY = "capacity"
    CONFLICT = "conflict"
    PAYLOAD_TOO_LARGE = "payload_too_large"


class AppError(Exception):
    """Application failure with an HTTP-mappable code; raised by services, handled at the API edge."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        document_id: str | None = None,
        cause: str | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.document_id = document_id
        self.cause = cause
        self.retry_after_seconds = retry_after_seconds


def http_status_for(error: AppError) -> int:
    """Map AppError codes to HTTP status for thin API adapters."""
    mapping: dict[ErrorCode, int] = {
        ErrorCode.BAD_REQUEST: 400,
        ErrorCode.NOT_FOUND: 404,
        ErrorCode.UNAUTHORIZED: 401,
        ErrorCode.FORBIDDEN: 403,
        ErrorCode.VALIDATION: 422,
        ErrorCode.PAYLOAD_TOO_LARGE: 413,
        ErrorCode.CONFLICT: 409,
        ErrorCode.RATE_LIMIT: 429,
        ErrorCode.CAPACITY: 503,
        ErrorCode.INFRA: 503,
        ErrorCode.EXTRACTION: 502,
        ErrorCode.RULES: 502,
        ErrorCode.SKIPPED: 200,
    }
    return mapping.get(error.code, 500)
