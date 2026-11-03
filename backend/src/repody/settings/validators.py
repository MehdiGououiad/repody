from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repody.settings.model import Settings

# Hard ceiling for Taskiq audit-run cancellation. Keep high enough for long OCR
# PDFs; defaults stay lower (see WorkerSettingsFields).
MAX_WORKER_TASK_TIMEOUT_MINUTES = 15


def validate_production_guardrails(settings: Settings) -> None:
    env = (settings.deployment_environment or "").strip().lower()
    if env != "production":
        return
    if not settings.oidc_enabled:
        raise ValueError(
            "AUDIT_OIDC_ENABLED must be true when AUDIT_DEPLOYMENT_ENVIRONMENT=production."
        )
    if (settings.extractor or "").strip().lower() == "stub":
        raise ValueError(
            "AUDIT_EXTRACTOR=stub is not allowed when AUDIT_DEPLOYMENT_ENVIRONMENT=production."
        )
    if (settings.inference_mode or "").strip().lower() == "stub":
        raise ValueError(
            "AUDIT_INFERENCE_MODE=stub is not allowed when AUDIT_DEPLOYMENT_ENVIRONMENT=production."
        )


def validate_timeout_alignment(settings: Settings) -> None:
    """Keep model HTTP timeouts and stale reap aligned with the worker task ceiling."""
    worker = settings.worker_task_timeout_minutes
    worker_seconds = worker * 60
    stale = settings.stale_run_timeout_minutes
    env = (settings.deployment_environment or "").strip().lower()
    is_prod = env == "production"

    checks = [("AUDIT_REPODY_VLM_TIMEOUT_SECONDS", settings.repody_vlm_timeout_seconds)]

    for label, seconds in checks:
        if seconds > worker_seconds:
            msg = f"{label} ({seconds}) must be <= worker task timeout ({worker_seconds}s)."
            if is_prod:
                raise ValueError(msg)
            warnings.warn(msg, stacklevel=1)

    if stale < worker + 1:
        msg = (
            f"AUDIT_STALE_RUN_TIMEOUT_MINUTES ({stale}) should be >= "
            f"worker task timeout + 1 ({worker + 1})."
        )
        if is_prod:
            raise ValueError(msg)
        warnings.warn(msg, stacklevel=1)
