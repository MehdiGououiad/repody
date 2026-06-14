"""Heuristics for remote vLLM cold-start (first request after GPU idle)."""

from __future__ import annotations

from audit_workbench.settings import Settings, get_settings

# First request after an idle GPU service is often much slower than steady-state.
GPU_COLD_START_THRESHOLD_MS = 15_000


def is_serverless_vllm(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return settings.inference_mode.lower() == "vllm"


def gpu_cold_start_likely(
    extraction_ms: int,
    *,
    cache_hit: bool = False,
    settings: Settings | None = None,
) -> bool:
    if cache_hit or extraction_ms < GPU_COLD_START_THRESHOLD_MS:
        return False
    return is_serverless_vllm(settings)
