from __future__ import annotations

from audit_workbench.settings import Settings, get_settings


def test_worker_task_timeout_reads_env(monkeypatch):
    monkeypatch.setenv("AUDIT_WORKER_TASK_TIMEOUT_MINUTES", "3")
    get_settings.cache_clear()
    settings = Settings()
    assert settings.worker_task_timeout_minutes == 3
