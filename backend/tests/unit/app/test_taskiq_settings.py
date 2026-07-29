from __future__ import annotations

from repody.settings import Settings, get_settings


def test_worker_task_timeout_reads_env(monkeypatch):
    monkeypatch.setenv("AUDIT_WORKER_TASK_TIMEOUT_MINUTES", "3")
    monkeypatch.setenv("AUDIT_REPODY_VLM_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("AUDIT_GLM_OCR_TIMEOUT_SECONDS", "60")
    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    assert settings.worker_task_timeout_minutes == 3
