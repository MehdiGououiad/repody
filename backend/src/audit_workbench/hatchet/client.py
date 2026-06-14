from __future__ import annotations

import os
from functools import lru_cache

from hatchet_sdk import Hatchet
from hatchet_sdk.config import ClientConfig

from audit_workbench.settings import get_settings


def _resolve_hatchet_token(settings) -> str:
    return (
        settings.hatchet_client_token
        or os.getenv("HATCHET_CLIENT_TOKEN")
        or os.getenv("AUDIT_HATCHET_CLIENT_TOKEN")
        or ""
    )


@lru_cache
def get_hatchet() -> Hatchet:
    settings = get_settings()
    token = _resolve_hatchet_token(settings)
    if not token:
        raise RuntimeError(
            "Hatchet token required when AUDIT_RUN_JOBS_INLINE=false "
            "(set HATCHET_CLIENT_TOKEN or AUDIT_HATCHET_CLIENT_TOKEN)"
        )
    config = ClientConfig(
        token=token,
        host_port=os.getenv("HATCHET_CLIENT_HOST_PORT") or settings.hatchet_client_host_port,
        server_url=os.getenv("HATCHET_CLIENT_SERVER_URL", "http://localhost:8888"),
    )
    if settings.hatchet_client_tls_strategy == "none":
        os.environ.setdefault("HATCHET_CLIENT_TLS_STRATEGY", "none")
    return Hatchet(config=config)


def clear_hatchet_client() -> None:
    get_hatchet.cache_clear()
