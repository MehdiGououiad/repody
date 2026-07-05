from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from audit_workbench.settings.model import Settings

MAX_WORKER_TASK_TIMEOUT_MINUTES = 3


def apply_inference_probe_defaults(settings: Settings) -> None:
    from audit_workbench.inference.runtime import is_remote_vllm_url

    if settings.inference_mode.lower() == "vllm":
        probe_env = os.getenv("AUDIT_GPU_LIVE_PROBE", "").strip().lower()
        health_env = os.getenv("AUDIT_HEALTHZ_PROBE_INFERENCE", "").strip().lower()
        probe_on = probe_env in ("true", "1", "yes")
        health_on = health_env in ("true", "1", "yes")
        if is_remote_vllm_url(settings.vllm_base_url):
            if not probe_on:
                settings.gpu_live_probe = False
            if not health_on:
                settings.healthz_probe_inference = False
        elif not probe_on:
            settings.gpu_live_probe = False
            if not health_on:
                settings.healthz_probe_inference = False
    elif os.getenv("AUDIT_GPU_LIVE_PROBE") is None:
        settings.gpu_live_probe = True


def validate_production_guardrails(settings: Settings) -> None:
    env = (settings.deployment_environment or "").strip().lower()
    if env != "production":
        return
    if not settings.oidc_enabled:
        raise ValueError(
            "AUDIT_OIDC_ENABLED must be true when AUDIT_DEPLOYMENT_ENVIRONMENT=production."
        )


def validate_timeout_alignment(settings: Settings) -> None:
    """Keep VLM HTTP and stale reap aligned with the 3-minute worker task ceiling."""
    worker = settings.worker_task_timeout_minutes
    worker_seconds = worker * 60
    vlm = settings.repody_vlm_timeout_seconds
    stale = settings.stale_run_timeout_minutes
    env = (settings.deployment_environment or "").strip().lower()
    is_prod = env == "production"

    if vlm > worker_seconds:
        msg = (
            f"AUDIT_REPODY_VLM_TIMEOUT_SECONDS ({vlm}) must be <= "
            f"worker task timeout ({worker_seconds}s)."
        )
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
