"""Drop every table, migrate to head and load the demo data (local development only)."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

from repody.app.seed import seed
from repody.infra import db


async def drop_schema() -> None:
    async with db.engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await db.engine.dispose()


async def load_demo() -> None:
    async with db.session_factory() as session:
        await seed(session)
        await session.commit()
    await db.engine.dispose()


if __name__ == "__main__":
    asyncio.run(drop_schema())
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
    )
    asyncio.run(load_demo())
    print("Database reset and seeded.")
