from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from audit_workbench.settings.model import Settings


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


def warn_postgres_create_all(settings: Settings) -> None:
    if settings.use_create_all and "postgresql" in settings.database_url.lower():
        warnings.warn(
            "AUDIT_USE_CREATE_ALL=true with PostgreSQL — prefer Alembic migrations in production.",
            stacklevel=1,
        )
