"""Ensure settings package exposes all production-critical fields."""

from __future__ import annotations

from audit_workbench.settings import Settings, clear_settings_cache, get_settings


def test_settings_package_imports():
    clear_settings_cache()
    settings = get_settings()
    assert settings.app_name
    assert settings.database_url
    assert settings.worker_pool in ("extract", "fast")
    assert settings.storage_backend in ("local", "s3")
    assert isinstance(settings.extraction_cache_enabled, bool)


def test_settings_required_fields_present():
    expected = {
        "database_url",
        "redis_url",
        "worker_pool",
        "worker_extract_max_jobs",
        "worker_fast_max_jobs",
        "inference_mode",
        "default_document_model_id",
        "repody_vlm_enabled",
        "rate_limit_enabled",
        "admission_control_enabled",
        "dispatch_max_attempts",
        "operator_actions_enabled",
        "otel_enabled",
    }
    missing = expected - set(Settings.model_fields)
    assert not missing, f"Missing settings fields: {missing}"
