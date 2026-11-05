"""Test setup.

Unit tests need nothing. Integration tests use a migrated Postgres database
(``repody_test``) and Redis from the local stack, an in-memory object store, and run
each queued run inline instead of on a Taskiq worker. Live tests (``-m live``) call a
running stack at E2E_API_URL.
"""

from __future__ import annotations

import os

# Before any `repody` import: settings are read once and cached.
os.environ.setdefault(
    "AUDIT_DATABASE_URL", "postgresql+asyncpg://audit:audit-local-dev@127.0.0.1:5432/repody_test"
)
os.environ.update(
    AUDIT_OIDC_ENABLED="false",
    AUDIT_OIDC_AUDIENCE="",
    AUDIT_SEED_ON_STARTUP="false",
    AUDIT_EXTRACTION_CACHE_TTL_SECONDS="0",
    AUDIT_LLAMACPP_BASE_URL="http://llamacpp.test/v1",
    OTEL_SDK_DISABLED="true",
)

import asyncio
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from repody.app import execute
from repody.extraction import client as inference
from repody.infra import db, queue
from repody.infra.storage import use_store
from repody.main import create_app
from repody.settings import get_settings

BACKEND = Path(__file__).resolve().parents[1]
FACTURE_PDF = BACKEND.parent / "e2e" / "fixtures" / "documents" / "Facture.pdf"


class MemoryStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    async def get(self, key: str) -> bytes:
        return self.objects[key]


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for kind in ("unit", "integration", "live"):
            if f"tests/{kind}/" in item.path.as_posix():
                item.add_marker(kind)


@pytest.fixture(scope="session")
async def database() -> None:
    """Create ``repody_test`` once and migrate it with Alembic, as in production."""
    url = get_settings().database_url
    name = url.rsplit("/", 1)[1]
    admin = await asyncpg.connect(url.replace("+asyncpg", "").rsplit("/", 1)[0] + "/postgres")
    try:
        await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()
    alembic = [sys.executable, "-m", "alembic", "upgrade", "head"]
    await asyncio.to_thread(subprocess.run, alembic, cwd=BACKEND, check=True)


@pytest.fixture
def model_answer(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """What the fake model server answers: set ``model_answer["text"]``; ``model_answer["calls"]``
    lists each request with the server it went to (None: the NuExtract server)."""
    answer: dict = {"text": "{}", "calls": []}

    async def chat(
        payload: dict, *, base_url: str | None = None, api_key: str | None = None
    ) -> str:
        answer["calls"].append({"request": payload, "base_url": base_url})
        return answer["text"]

    monkeypatch.setattr(inference, "chat", chat)
    return answer


@pytest.fixture
async def api(
    database, monkeypatch: pytest.MonkeyPatch, model_answer
) -> AsyncIterator[AsyncClient]:
    """The app on a clean database; a dispatched run is processed before the request returns."""
    async with db.engine.begin() as conn:
        tables = ", ".join(t.name for t in reversed(db.Base.metadata.sorted_tables))
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))

    async def run_inline(run_id: str) -> bool:
        await execute.process_run(run_id)
        return True

    monkeypatch.setattr(queue, "dispatch", run_inline)
    use_store(MemoryStore())
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        yield client
    use_store(None)
    await db.engine.dispose()
