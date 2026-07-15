"""Heuristics for remote inference cold-start (first request after GPU idle)."""

from __future__ import annotations

from audit_workbench.inference.runtime import is_remote_inference_url
from audit_workbench.settings import Settings, get_settings

GPU_COLD_START_THRESHOLD_MS = 15_000


def is_serverless_inference(settings: Settings | None = None) -> bool:
    """True for remote OpenAI-compatible inference, not local llama-server."""
    settings = settings or get_settings()
    if settings.inference_mode.lower() != "llamacpp":
        return False
    return is_remote_inference_url(settings.llamacpp_base_url)


def gpu_cold_start_likely(
    extraction_ms: int,
    *,
    cache_hit: bool = False,
    settings: Settings | None = None,
) -> bool:
    if cache_hit or extraction_ms < GPU_COLD_START_THRESHOLD_MS:
        return False
    return is_serverless_inference(settings)
