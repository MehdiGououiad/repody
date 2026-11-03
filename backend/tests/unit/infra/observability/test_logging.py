from __future__ import annotations

from repody.infra.observability.logging import _redact_sensitive_fields
from repody.settings import Settings


def _process_event(event_dict: dict) -> dict:
    return dict(_redact_sensitive_fields(None, "", dict(event_dict)))


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

    from repody.infra.observability.logging import configure_logging

    settings = Settings(log_json=True)
    configure_logging(settings)
    get_logger("test").info("logging_smoke", event_domain="test")


def test_error_log_keeps_exc_info_for_sentry() -> None:
    import logging

    import structlog

    from repody.infra.observability.logging import configure_logging

    settings = Settings(log_json=True)
    configure_logging(settings)
    records: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    root = logging.getLogger()
    capture = _Capture()
    capture.setLevel(logging.ERROR)
    root.addHandler(capture)
    try:
        raise RuntimeError("probe-exc")
    except RuntimeError:
        structlog.get_logger("probe-exc-info").error("probe_failed", exc_info=True)
    finally:
        root.removeHandler(capture)

    matched = [
        record
        for record in records
        if isinstance(record.msg, dict) and record.msg.get("event") == "probe_failed"
    ]
    assert matched
    assert matched[-1].exc_info is not None
    assert matched[-1].exc_info[0] is RuntimeError
    formatted = root.handlers[0].format(matched[-1])
    assert "probe_failed" in formatted
    assert "probe-exc" in formatted


def test_configure_logging_writes_log_file(tmp_path) -> None:
    from repody.infra.observability.logging import configure_logging

    log_path = tmp_path / "repody-api.log"
    settings = Settings(log_json=True, log_file=str(log_path))
    configure_logging(settings)
    assert log_path.exists()
    assert "logging_configured" in log_path.read_text(encoding="utf-8")
