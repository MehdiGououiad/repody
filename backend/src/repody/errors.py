"""The one application exception; ``main`` turns it into an HTTP error response."""

from __future__ import annotations


class AppError(Exception):
    def __init__(self, status_code: int, detail: str, *, retry_after: int | None = None) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.retry_after = retry_after
