"""Shared API assertion helpers — contract-style checks for HTTP + AppError mapping."""

from __future__ import annotations

from typing import Any

from httpx import Response

from audit_workbench.runtime.contracts.result import AppError, ErrorCode, http_status_for


def assert_app_error_status(code: ErrorCode, expected_status: int) -> None:
    """Unit seam: ErrorCode → HTTP status mapping stays stable."""
    assert http_status_for(AppError(code=code, message="x")) == expected_status


def assert_error_response(
    response: Response,
    *,
    status_code: int,
    detail_contains: str | None = None,
) -> dict[str, Any]:
    """Integration seam: FastAPI HTTPException detail contract."""
    assert response.status_code == status_code, response.text
    body: Any
    try:
        body = response.json()
    except Exception:
        body = {"detail": response.text}
    detail = body.get("detail") if isinstance(body, dict) else body
    if detail_contains is not None:
        text = detail if isinstance(detail, str) else str(detail)
        assert detail_contains in text, f"expected {detail_contains!r} in {text!r}"
    return body if isinstance(body, dict) else {"detail": detail}
