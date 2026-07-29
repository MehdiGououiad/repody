"""Unit: AppError → HTTP status contract (API adapters depend on this map)."""

from __future__ import annotations

import pytest

from audit_workbench.runtime.contracts.result import ErrorCode
from tests.helpers.api_errors import assert_app_error_status


@pytest.mark.parametrize(
    ("code", "status"),
    [
        (ErrorCode.VALIDATION, 422),
        (ErrorCode.FORBIDDEN, 403),
        (ErrorCode.UNAUTHORIZED, 401),
        (ErrorCode.NOT_FOUND, 404),
        (ErrorCode.CONFLICT, 409),
        (ErrorCode.PAYLOAD_TOO_LARGE, 413),
        (ErrorCode.RATE_LIMIT, 429),
        (ErrorCode.CAPACITY, 503),
        (ErrorCode.INFRA, 503),
        (ErrorCode.EXTRACTION, 502),
        (ErrorCode.RULES, 502),
        (ErrorCode.SKIPPED, 200),
    ],
)
def test_http_status_for_error_codes(code: ErrorCode, status: int):
    assert_app_error_status(code, status)
