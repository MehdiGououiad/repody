from __future__ import annotations

from urllib.parse import urlparse

from audit_workbench.settings import Settings, get_settings

_LOCAL_VLLM_HOSTS = frozenset(
    {
        "localhost",
        "127.0.0.1",
        "vllm",
        "host.docker.internal",
        "model-runner.docker.internal",
    }
)


def _hostname(base_url: str) -> str:
    return (urlparse(base_url.rstrip("/")).hostname or "").lower()


def is_local_vllm_url(base_url: str) -> bool:
    host = _hostname(base_url)
    if not host:
        return True
    if host in _LOCAL_VLLM_HOSTS:
        return True
    return host.endswith(".internal")


def is_remote_vllm_url(base_url: str) -> bool:
    return not is_local_vllm_url(base_url)


def openai_api_key_for_base_url(base_url: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    normalized = base_url.rstrip("/")
    vllm_base = settings.vllm_base_url.rstrip("/")
    if normalized.startswith(vllm_base) or normalized == vllm_base:
        return settings.vllm_api_key or "local"
    return "local"


def inference_mode(settings: Settings | None = None) -> str:
    from audit_workbench.settings import get_settings

    return (settings or get_settings()).inference_mode.lower()


def openai_base_url_for_runtime(runtime: str, settings: Settings | None = None) -> str:
    from audit_workbench.settings import get_settings

    settings = settings or get_settings()
    if runtime == "vllm":
        return settings.vllm_base_url.rstrip("/")
    return settings.docker_model_runner_base_url.rstrip("/")


def default_document_runtime(settings: Settings | None = None) -> str:
    mode = inference_mode(settings)
    if mode == "vllm":
        return "vllm"
    return "docker_model_runner"


def remote_vllm_endpoint(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    return (
        settings.inference_mode.lower() == "vllm"
        and is_remote_vllm_url(settings.vllm_base_url)
    )


def openai_probe_timeout_seconds(base_url: str, *, default: float = 2.0) -> float:
    """Remote vLLM may need extra time on first request after idle."""
    if is_remote_vllm_url(base_url):
        return 30.0
    return default
