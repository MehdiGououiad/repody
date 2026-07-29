"""Result and AppError — errors as data at pipeline boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

T = TypeVar("T")


class ErrorCode(StrEnum):
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


@dataclass(frozen=True, slots=True)
class AppError:
    code: ErrorCode
    message: str
    document_id: str | None = None
    cause: str | None = None
    retry_after_seconds: int | None = None


@dataclass(frozen=True, slots=True)
class Result(Generic[T]):
    value: T | None = None
    error: AppError | None = None

    @staticmethod
    def ok(value: T) -> Result[T]:
        return Result(value=value)

    @staticmethod
    def fail(error: AppError) -> Result[T]:
        return Result(error=error)

    @property
    def is_ok(self) -> bool:
        return self.error is None

    def unwrap(self) -> T:
        # None is a valid success value (e.g. Result[list[str] | None]).
        if self.error is not None:
            raise ValueError(self.error.message)
        return self.value  # type: ignore[return-value]


def http_status_for(error: AppError) -> int:
    """Map AppError codes to HTTP status for thin API adapters."""
    mapping: dict[ErrorCode, int] = {
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
