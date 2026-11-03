from __future__ import annotations

from repody.settings import Settings, get_settings


def llamacpp_base_url(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return settings.llamacpp_base_url.rstrip("/")


def openai_api_key_for_base_url(base_url: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if base_url.rstrip("/").startswith(llamacpp_base_url(settings)):
        return settings.llamacpp_api_key or "local"
    return "local"
