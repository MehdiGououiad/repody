#!/usr/bin/env python3
"""Apply Alembic migrations to head."""
from __future__ import annotations

import asyncio
import subprocess
import sys

from audit_workbench.db.base import engine


async def _bootstrap() -> None:
    print("Running alembic upgrade head…", flush=True)
    await asyncio.to_thread(
        subprocess.run,
        ["alembic", "upgrade", "head"],
        check=True,
        cwd="/app",
    )
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
