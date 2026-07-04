"""Postgres test database helpers — Alembic migrations, same path as production."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Register ORM tables on Base.metadata before truncate helpers run.
import audit_workbench.db.models  # noqa: F401
from audit_workbench.db.base import Base
from audit_workbench.db.seed import seed_database
from audit_workbench.settings import clear_settings_cache

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://audit:audit-local-dev@127.0.0.1:5432/audit_workbench_test"
)


def resolve_test_database_url() -> str:
    return os.environ.get("AUDIT_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)


def configure_test_database_url(url: str | None = None) -> str:
    resolved = url or resolve_test_database_url()
    os.environ["AUDIT_DATABASE_URL"] = resolved
    clear_settings_cache()
    return resolved


def upgrade_database_to_head(database_url: str | None = None) -> None:
    """Apply Alembic migrations (subprocess — safe inside pytest-asyncio)."""
    url = configure_test_database_url(database_url)
    env = os.environ.copy()
    env["AUDIT_DATABASE_URL"] = url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Alembic upgrade failed for test database:\n{result.stderr or result.stdout}"
        )


def create_test_engine(database_url: str | None = None) -> AsyncEngine:
    url = configure_test_database_url(database_url)
    # NullPool: avoid asyncpg connections bound to a stale event loop between tests.
    return create_async_engine(url, poolclass=NullPool, pool_pre_ping=True)


async def reset_test_database(session_factory: async_sessionmaker) -> None:
    """Truncate all tables and re-seed — one clean slate per test."""
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    async with session_factory() as session:
        # Release locks from aborted prior runs (local dev / killed pytest).
        await session.execute(
            text(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid <> pg_backend_pid()"
            )
        )
        if table_names:
            await session.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
        await session.commit()
    async with session_factory() as session:
        await seed_database(session)
        await session.commit()


async def ensure_postgres_database(database_url: str | None = None) -> None:
    """Create the test database when missing (local dev); CI usually pre-creates it."""
    url = configure_test_database_url(database_url)
    if not url.startswith("postgresql"):
        return

    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    db_name = parsed.database
    if not db_name:
        return

    admin_url = parsed.set(database="postgres")
    engine = create_async_engine(admin_url.render_as_string(hide_password=False))
    try:
        async with engine.connect() as conn:
            conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
            exists = (
                await conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": db_name},
                )
            ).scalar()
            if exists is None:
                await conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        await engine.dispose()


def bind_test_database(
    engine: AsyncEngine,
    session_factory: async_sessionmaker,
) -> None:
    import audit_workbench.api.deps as deps
    import audit_workbench.db.base as db_base
    import audit_workbench.main as main_mod

    db_base.engine = engine
    db_base.async_session_factory = session_factory
    deps.async_session_factory = session_factory
    main_mod.engine = engine


def patch_session_factory(
    monkeypatch,
    session_factory: async_sessionmaker,
) -> None:
    import audit_workbench.api.deps as deps
    import audit_workbench.db.base as db_base

    monkeypatch.setattr(db_base, "async_session_factory", session_factory)
    monkeypatch.setattr(deps, "async_session_factory", session_factory)
