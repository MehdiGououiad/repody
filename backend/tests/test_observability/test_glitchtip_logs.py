import pytest

from audit_workbench.observability.glitchtip_logs import should_forward_log_level


def test_should_forward_respects_level(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "http://key@localhost:8090/1")
    monkeypatch.setenv("SENTRY_ENABLE_LOGS", "true")
    monkeypatch.setenv("SENTRY_LOG_LEVEL", "WARNING")

    assert not should_forward_log_level("info")
    assert should_forward_log_level("warning")
    assert should_forward_log_level("error")


def test_should_forward_disabled_without_dsn(monkeypatch) -> None:
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setenv("SENTRY_ENABLE_LOGS", "true")

    assert not should_forward_log_level("error")


def test_should_forward_disabled_on_workers(monkeypatch) -> None:
    monkeypatch.setenv("SENTRY_DSN", "http://key@localhost:8090/1")
    monkeypatch.setenv("SENTRY_ENABLE_LOGS", "false")

    assert not should_forward_log_level("error")
