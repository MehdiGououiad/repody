from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from repody.infra.db import base as db_base


def _session_factory():
    return db_base.async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Yield a request-scoped session. Callers that mutate must ``await session.commit()``."""
    async with _session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


SessionDep = Annotated[AsyncSession, Depends(get_session)]
