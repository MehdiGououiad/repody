from __future__ import annotations

from audit_workbench.observability.logging import _redact_sensitive_fields
from audit_workbench.settings import Settings


def _process_event(event_dict: dict) -> dict:
    return _redact_sensitive_fields(None, "", dict(event_dict))


def test_redact_sensitive_fields_masks_tokens() -> None:
    event = {
        "event": "run_create_unauthorized",
        "admin_api_token": "secret-value",
        "authorization": "Bearer abc",
        "workflow_id": "wf_123",
    }
    redacted = _process_event(event)
    assert redacted["admin_api_token"] == "***REDACTED***"
    assert redacted["authorization"] == "***REDACTED***"
    assert redacted["workflow_id"] == "wf_123"


def test_configure_logging_json_smoke() -> None:
    from structlog import get_logger

    from audit_workbench.observability.logging import configure_logging

    settings = Settings(log_json=True, otel_service_name="test-service")
    configure_logging(settings)
    get_logger("test").info("logging_smoke", event_domain="test")
