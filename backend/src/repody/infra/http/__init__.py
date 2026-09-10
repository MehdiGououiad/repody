"""Shared HTTP client helpers (httpx connection pooling)."""

from repody.infra.http.clients import close_http_clients, get_http_client

__all__ = ["close_http_clients", "get_http_client"]
