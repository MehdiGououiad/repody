from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from audit_workbench.db import base as db_base


def _session_factory():
    return db_base.async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with _session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
