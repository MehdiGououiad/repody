from __future__ import annotations

import pytest

from repody.settings import Settings, clear_settings_cache


@pytest.fixture(autouse=True)
def _clear_settings():
    clear_settings_cache()
    yield
    clear_settings_cache()


def _settings(**kwargs: object) -> Settings:
    """Build Settings without loading repo ``.env`` (tests must be hermetic)."""
    return Settings(_env_file=None, **kwargs)  # type: ignore[arg-type]


def test_production_requires_oidc(monkeypatch):
    monkeypatch.setenv("AUDIT_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "false")
    with pytest.raises(ValueError, match="OIDC_ENABLED must be true"):
        _settings()


def test_production_allows_oidc_when_enabled(monkeypatch):
    monkeypatch.setenv("AUDIT_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "true")
    monkeypatch.setenv("AUDIT_OIDC_ISSUER", "https://auth.example.com/realms/repody")
    settings = _settings()
    assert settings.oidc_enabled is True


def test_development_allows_oidc_disabled(monkeypatch):
    monkeypatch.setenv("AUDIT_DEPLOYMENT_ENVIRONMENT", "development")
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "false")
    settings = _settings()
    assert settings.oidc_enabled is False


def test_production_rejects_vlm_timeout_above_worker(monkeypatch):
    monkeypatch.setenv("AUDIT_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "true")
    monkeypatch.setenv("AUDIT_OIDC_ISSUER", "https://auth.example.com/realms/repody")
    monkeypatch.setenv("AUDIT_WORKER_TASK_TIMEOUT_MINUTES", "3")
    monkeypatch.setenv("AUDIT_REPODY_VLM_TIMEOUT_SECONDS", "600")
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("AUDIT_GLM_OCR_TIMEOUT_SECONDS", "60")
    with pytest.raises(ValueError, match="REPODY_VLM_TIMEOUT_SECONDS"):
        _settings()


def test_production_rejects_paddle_timeout_above_worker(monkeypatch):
    monkeypatch.setenv("AUDIT_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("AUDIT_OIDC_ENABLED", "true")
    monkeypatch.setenv("AUDIT_OIDC_ISSUER", "https://auth.example.com/realms/repody")
    monkeypatch.setenv("AUDIT_WORKER_TASK_TIMEOUT_MINUTES", "3")
    monkeypatch.setenv("AUDIT_REPODY_VLM_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("AUDIT_PADDLEOCR_V6_TIMEOUT_SECONDS", "900")
    monkeypatch.setenv("AUDIT_GLM_OCR_TIMEOUT_SECONDS", "60")
    with pytest.raises(ValueError, match="PADDLEOCR_V6_TIMEOUT_SECONDS"):
        _settings()


def test_worker_task_timeout_cannot_exceed_fifteen_minutes(monkeypatch):
    monkeypatch.setenv("AUDIT_WORKER_TASK_TIMEOUT_MINUTES", "16")
    with pytest.raises(ValueError):
        _settings()


def test_defaults_cap_task_at_three_minutes():
    settings = _settings()
    assert settings.worker_task_timeout_minutes == 3
    assert settings.repody_vlm_timeout_seconds <= 180
    assert settings.stale_run_timeout_minutes > settings.worker_task_timeout_minutes
