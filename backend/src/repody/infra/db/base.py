from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from repody.settings import get_settings


class Base(DeclarativeBase):
    pass


def _engine():
    settings = get_settings()
    kwargs: dict = {
        "echo": settings.debug,
        "pool_pre_ping": True,
        "pool_size": settings.db_pool_size,
        "max_overflow": settings.db_max_overflow,
        "pool_timeout": settings.db_pool_timeout,
    }
    return create_async_engine(settings.database_url, **kwargs)


engine = _engine()
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
