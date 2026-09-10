"""Shared httpx AsyncClient pool."""

from __future__ import annotations

import pytest

from repody.infra.http import close_http_clients, get_http_client


@pytest.mark.asyncio
async def test_get_http_client_reuses_same_instance():
    await close_http_clients()
    first = get_http_client(base_url="https://example.test")
    second = get_http_client(base_url="https://example.test")
    assert first is second
    await close_http_clients()
    third = get_http_client(base_url="https://example.test")
    assert third is not first
    await close_http_clients()


@pytest.mark.asyncio
async def test_get_http_client_separates_by_headers():
    await close_http_clients()
    a = get_http_client(headers={"Authorization": "Bearer a"})
    b = get_http_client(headers={"Authorization": "Bearer b"})
    assert a is not b
    await close_http_clients()
