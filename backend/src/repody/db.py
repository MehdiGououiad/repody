"""Async SQLAlchemy engine and sessions."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from repody.settings import get_settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    get_settings().database_url, pool_size=get_settings().db_pool_size, pool_pre_ping=True
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


def bind(new_engine, new_factory: async_sessionmaker[AsyncSession]) -> None:
    """Point the app at another database (tests)."""
    global engine, session_factory
    engine, session_factory = new_engine, new_factory
