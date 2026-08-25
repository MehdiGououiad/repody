"""Enqueue + auth Result boundary (unit — no HTTP)."""

from __future__ import annotations

from repody.app.run.enqueue import client_key_from_request
from repody.runtime.contracts.result import AppError, ErrorCode, Result


def test_client_key_from_api_bearer_hashes_token() -> None:
    key = client_key_from_request(
        "api",
        "Bearer super-secret-token",
        client_host="1.2.3.4",
    )
    assert key is not None
    assert len(key) == 16
    assert key != "super-secret-token"


def test_client_key_from_test_source_uses_host() -> None:
    assert client_key_from_request("test", None, "9.9.9.9") == "9.9.9.9"


def test_result_fail_preserves_capacity_retry() -> None:
    err = AppError(
        code=ErrorCode.CAPACITY,
        message="queue full",
        retry_after_seconds=60,
    )
    result: Result[str] = Result.fail(err)
    assert not result.is_ok
    assert result.error is not None
    assert result.error.retry_after_seconds == 60
