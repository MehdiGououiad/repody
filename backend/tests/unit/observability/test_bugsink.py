from audit_workbench.observability.bugsink import bugsink_enabled, init_bugsink


def test_bugsink_disabled_without_dsn(monkeypatch):
    monkeypatch.delenv("BUGSINK_DSN", raising=False)
    assert bugsink_enabled() is False
    init_bugsink("repody-api")


def test_bugsink_enabled_with_dsn(monkeypatch):
    monkeypatch.setenv("BUGSINK_DSN", "http://key@localhost:8090/1")
    assert bugsink_enabled() is True
    init_bugsink("repody-api")
