"""Classify inference endpoint URLs as local (same host / container network) or remote."""

from __future__ import annotations

from urllib.parse import urlparse

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "host.docker.internal"})


def is_local_inference_url(base_url: str) -> bool:
    host = (urlparse(base_url.rstrip("/")).hostname or "").lower()
    if not host or host in _LOCAL_HOSTS:
        return True
    return host.endswith(".internal")


def is_remote_inference_url(base_url: str) -> bool:
    return not is_local_inference_url(base_url)
