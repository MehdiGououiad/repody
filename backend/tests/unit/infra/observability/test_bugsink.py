import repody.infra.observability.bugsink as bugsink
from repody.infra.observability.bugsink import bugsink_enabled, init_bugsink


def _reset_init() -> None:
    bugsink._initialized = False


def test_bugsink_disabled_without_dsn(monkeypatch):
    _reset_init()
    monkeypatch.delenv("BUGSINK_DSN", raising=False)
    called = {"n": 0}

    def fail_init(**_kwargs):
        called["n"] += 1

    monkeypatch.setattr(bugsink.sentry_sdk, "init", fail_init)
    assert bugsink_enabled() is False
    init_bugsink("repody-api")
    assert called["n"] == 0


def test_bugsink_init_follows_sdk_recommendations(monkeypatch):
    _reset_init()
    monkeypatch.setenv("BUGSINK_DSN", "http://key@bugsink:8000/1")
    monkeypatch.setenv("BUGSINK_RELEASE", "0.1.0")
    monkeypatch.setenv("AUDIT_DEPLOYMENT_ENVIRONMENT", "development")
    captured: dict[str, object] = {}

    def fake_init(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(bugsink.sentry_sdk, "init", fake_init)
    assert bugsink_enabled() is True
    init_bugsink("repody-api")

    assert captured["dsn"] == "http://key@bugsink:8000/1"
    assert captured["send_default_pii"] is True
    assert captured["max_request_body_size"] == "always"
    assert captured["traces_sample_rate"] == 0
    assert captured["send_client_reports"] is False
    assert captured["auto_session_tracking"] is False
    assert captured["release"] == "0.1.0"
    assert captured["server_name"] == "repody-api"
    integrations = captured["integrations"]
    assert isinstance(integrations, list)
    by_name = {type(item).__name__: item for item in integrations}
    assert set(by_name) == {
        "StarletteIntegration",
        "FastApiIntegration",
        "LoggingIntegration",
    }
    assert by_name["LoggingIntegration"].capture_sentry_logs is False
    assert captured["before_send"] is bugsink._before_send
    assert captured["before_breadcrumb"] is bugsink._before_breadcrumb


def test_before_send_uses_structlog_event_name():
    import logging

    record = logging.LogRecord(
        name="probe",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg={
            "event": "probe_failed",
            "trace_id": "abc",
            "exc_info": (RuntimeError, RuntimeError("x"), None),
        },
        args=(),
        exc_info=None,
    )
    event = {
        "logentry": {"message": str(record.msg), "formatted": str(record.msg)},
        "extra": {},
    }
    sent = bugsink._before_send(event, {"log_record": record})
    assert sent["logentry"]["message"] == "probe_failed"
    assert sent["logentry"]["formatted"] == "probe_failed"
    assert sent["extra"]["trace_id"] == "abc"
    assert "exc_info" not in sent["extra"]
