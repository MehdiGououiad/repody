"""P0 scalability: skip-locked dialect gate."""

from __future__ import annotations

from types import SimpleNamespace

from repody.app.run.dispatch_outbox import _supports_skip_locked


def test_supports_skip_locked_only_on_postgres():
    pg = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    )
    assert _supports_skip_locked(pg) is True

    sqlite = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    )
    assert _supports_skip_locked(sqlite) is False
