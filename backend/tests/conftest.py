"""Test setup.

Unit tests need nothing. Integration tests use a migrated Postgres database
(``repody_test``) and Redis from the local stack, an in-memory object store, and run
each queued run inline instead of on a Taskiq worker. Live tests (``-m live``) call a
running stack at E2E_API_URL.
"""

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
from typing import BinaryIO

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from repody.app import execute
from repody.app.seed import seed
from repody.extraction import client as inference
from repody.infra import db, queue
from repody.infra.storage import use_store
from repody.main import create_app
from repody.settings import get_settings

BACKEND = Path(__file__).resolve().parents[1]


class MemoryStore:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, file: BinaryIO, content_type: str) -> None:
        self.objects[key] = file.read()

    async def get(self, key: str) -> bytes:
        return self.objects[key]

    async def delete(self, keys: list[str]) -> None:
        for key in keys:
            self.objects.pop(key, None)


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        for kind in ("unit", "integration", "live"):
            if f"tests/{kind}/" in item.path.as_posix():
                item.add_marker(kind)


@pytest.fixture(scope="session")
async def database() -> AsyncIterator[None]:
    """Create ``repody_test`` once and migrate it with Alembic, as in production."""
    url = get_settings().database_url.get_secret_value()
    name = url.rsplit("/", 1)[1]
    admin = await asyncpg.connect(url.replace("+asyncpg", "").rsplit("/", 1)[0] + "/postgres")
    try:
        await admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await admin.execute(f'CREATE DATABASE "{name}"')
    finally:
        await admin.close()
    alembic = [sys.executable, "-m", "alembic", "upgrade", "head"]
    await asyncio.to_thread(subprocess.run, alembic, cwd=BACKEND, check=True)
    yield
    await db.engine.dispose()


@pytest.fixture
def model_answer(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """What the fake model server answers: set ``model_answer["text"]`` (and ``["truncated"]``
    for an answer cut off at the token limit); ``model_answer["calls"]`` lists each request."""
    answer: dict = {"text": "{}", "truncated": False, "calls": []}

    async def chat(
        payload: dict,
    ) -> inference.Reply:
        answer["calls"].append({"request": payload})
        return inference.Reply(text=answer["text"], truncated=answer["truncated"])

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


@pytest.fixture
async def seeded(api: AsyncClient) -> None:
    """The demo workflow and its audit (repody.app.seed) on the clean test database."""
    async with db.session_factory() as session:
        await seed(session)
        await session.commit()
