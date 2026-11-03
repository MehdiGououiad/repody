from __future__ import annotations

from repody.settings import Settings, get_settings
from repody.util.urls import is_remote_inference_url

# An extraction slower than this on a remote endpoint probably waited for a GPU to wake.
GPU_COLD_START_THRESHOLD_MS = 15_000


def llamacpp_base_url(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return settings.llamacpp_base_url.rstrip("/")


def openai_api_key_for_base_url(base_url: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if base_url.rstrip("/").startswith(llamacpp_base_url(settings)):
        return settings.llamacpp_api_key or "local"
    return "local"


def is_serverless_inference(settings: Settings | None = None) -> bool:
    """True when the llama-server endpoint is remote (serverless GPU), not on this host."""
    settings = settings or get_settings()
    return is_remote_inference_url(settings.llamacpp_base_url)


def gpu_cold_start_likely(extraction_ms: int, *, settings: Settings | None = None) -> bool:
    return extraction_ms >= GPU_COLD_START_THRESHOLD_MS and is_serverless_inference(settings)
