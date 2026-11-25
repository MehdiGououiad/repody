"""Test setup.

Unit tests need nothing. Integration tests use a migrated Postgres database
(``repody_test``) from the local stack, an in-memory object store, and run each queued
run inline instead of on a Hatchet worker. Live tests (``-m live``) call a
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
    AUDIT_INFERENCE_BASE_URL="http://llamacpp.test/v1",
    OTEL_SDK_DISABLED="true",
)

import asyncio
import base64
import io
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import BinaryIO

import asyncpg
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image
from sqlalchemy import text

from repody.app import execute
from repody.app.seed import seed
from repody.extraction import client as inference
from repody.extraction import render
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


def _is_second_read(payload: dict) -> bool:
    """Whether a request is a second read: its first page is sent at half the pixels."""
    parts = payload["messages"][-1]["content"]
    if not parts or parts[0].get("type") != "image_url":
        return False
    png = base64.b64decode(parts[0]["image_url"]["url"].split(",", 1)[1])
    width, height = Image.open(io.BytesIO(png)).size
    return width * height < 0.75 * render.MIN_MODEL_PIXELS


@pytest.fixture
def model_answer(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """What the fake model server answers: set ``model_answer["text"]`` (and ``["truncated"]``
    for an answer cut off at the token limit, ``["asleep"]`` for a server that has to start).
    The second read (AUDIT_SECOND_READ) gets the same answer, or ``["check_text"]`` when set,
    and raises ``["check_error"]`` when set. ``model_answer["calls"]`` lists each request, with
    ``check`` true for a second read."""
    answer: dict = {
        "text": "{}",
        "truncated": False,
        "asleep": False,
        "calls": [],
        "wakes": 0,
        "check_text": None,
        "check_error": None,
    }

    async def wake(on_asleep) -> bool:
        answer["wakes"] += 1
        if answer["asleep"]:
            await on_asleep()
        return answer["asleep"]

    async def chat(
        payload: dict,
    ) -> inference.Reply:
        check = _is_second_read(payload)
        answer["calls"].append({"request": payload, "check": check})
        if check and answer["check_error"]:
            raise answer["check_error"]
        text = answer["check_text"] if check and answer["check_text"] is not None else None
        return inference.Reply(text=text or answer["text"], truncated=answer["truncated"])

    monkeypatch.setattr(inference, "chat", chat)
    monkeypatch.setattr(inference, "wake", wake)
    return answer


@pytest.fixture
def cancelled() -> list[str]:
    """The Hatchet runs the ``api`` fixture's app cancelled."""
    return []


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """The app, built once per test process (building it takes about 0.15s, and most tests
    use it). It keeps no state between requests: each test still gets a clean database, a new
    store and its own fakes (``api``). A test that needs dependency overrides or other settings
    builds its own with ``create_app()``."""
    return create_app()


@pytest.fixture
async def api(
    database, app: FastAPI, monkeypatch: pytest.MonkeyPatch, model_answer, cancelled: list[str]
) -> AsyncIterator[AsyncClient]:
    """The app on a clean database, without Hatchet: a run is processed before the request
    returns, and the ``cancelled`` fixture lists the Hatchet runs cancelled."""
    async with db.engine.begin() as conn:
        tables = ", ".join(t.name for t in reversed(db.Base.metadata.sorted_tables))
        await conn.execute(text(f"TRUNCATE {tables} CASCADE"))

    async def run_inline(run_id: str, _client_key: str) -> str:
        await execute.process_run(run_id)
        return f"task-{run_id}"

    async def cancel(task_run_id: str) -> None:
        cancelled.append(task_run_id)

    monkeypatch.setattr(queue, "dispatch", run_inline)
    monkeypatch.setattr(queue, "cancel", cancel)
    use_store(MemoryStore())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    use_store(None)


@pytest.fixture
async def seeded(api: AsyncClient) -> None:
    """The demo workflow and its audit (repody.app.seed) on the clean test database."""
    async with db.session_factory() as session:
        await seed(session)
        await session.commit()
