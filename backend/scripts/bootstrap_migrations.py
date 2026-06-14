#!/usr/bin/env python3
"""Apply Alembic migrations; stamp baseline when DB was created via create_all."""
from __future__ import annotations

import asyncio
import subprocess
import sys

from sqlalchemy import text

from audit_workbench.db.base import engine

BASELINE_REVISION = "9b24af3aa3c5"


async def _table_exists(conn, name: str) -> bool:
    row = (
        await conn.execute(
            text("SELECT to_regclass(:qualified)"),
            {"qualified": f"public.{name}"},
        )
    ).scalar()
    return row is not None


async def _current_revision(conn) -> str | None:
    if not await _table_exists(conn, "alembic_version"):
        return None
    return (
        await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
    ).scalar()


async def _bootstrap() -> None:
    async with engine.connect() as conn:
        revision = await _current_revision(conn)
        legacy_schema = await _table_exists(conn, "workflows") or await _table_exists(
            conn, "rule_templates"
        )

    if revision is None and legacy_schema:
        print(
            f"Existing schema detected without Alembic history — stamping {BASELINE_REVISION}",
            flush=True,
        )
        subprocess.run(["alembic", "stamp", BASELINE_REVISION], check=True, cwd="/app")

    print("Running alembic upgrade head…", flush=True)
    subprocess.run(["alembic", "upgrade", "head"], check=True, cwd="/app")
    await engine.dispose()


def main() -> int:
    asyncio.run(_bootstrap())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Migration failed (exit {exc.returncode})", file=sys.stderr, flush=True)
        raise SystemExit(exc.returncode) from exc
