from __future__ import annotations

from urllib.parse import urlparse

from audit_workbench.settings import Settings, get_settings

DOCUMENT_RUNTIME = "llamacpp"

_LOCAL_INFERENCE_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "host.docker.internal",
    }
)


def _hostname(base_url: str) -> str:
    return (urlparse(base_url.rstrip("/")).hostname or "").lower()


def is_local_inference_url(base_url: str) -> bool:
    host = _hostname(base_url)
    if not host:
        return True
    if host in _LOCAL_INFERENCE_HOSTS:
        return True
    return host.endswith(".internal")


def is_remote_inference_url(base_url: str) -> bool:
    return not is_local_inference_url(base_url)


def llamacpp_base_url(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return settings.llamacpp_base_url.rstrip("/")


def openai_api_key_for_base_url(base_url: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    normalized = base_url.rstrip("/")
    inference_base = llamacpp_base_url(settings)
    if normalized.startswith(inference_base) or normalized == inference_base:
        return settings.llamacpp_api_key or "local"
    return "local"


def inference_mode(settings: Settings | None = None) -> str:
    return (settings or get_settings()).inference_mode.lower()


def remote_inference_endpoint(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return (
        settings.inference_mode.lower() == "llamacpp"
        and is_remote_inference_url(llamacpp_base_url(settings))
    )


def openai_probe_timeout_seconds(base_url: str, *, default: float = 2.0) -> float:
    """Remote inference may need extra time on first request after idle."""
    if is_remote_inference_url(base_url):
        return 30.0
    return default
