#!/usr/bin/env python3
"""Drop app schema, re-apply Alembic migrations, and seed demo data."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from audit_workbench.db.base import async_session_factory, engine
from audit_workbench.db.seed import seed_database

BACKEND_ROOT = Path(__file__).resolve().parents[1]


async def _drop_public_schema() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    await engine.dispose()


def _run_alembic_upgrade() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


async def _seed() -> None:
    async with async_session_factory() as session:
        await seed_database(session)
        await session.commit()


async def main() -> int:
    print("Dropping public schema…", flush=True)
    await _drop_public_schema()
    print("Applying Alembic migrations…", flush=True)
    _run_alembic_upgrade()
    print("Seeding demo data…", flush=True)
    await _seed()
    print("Database reset complete.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
