"""Async SQLAlchemy engine and sessions."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from repody.settings import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
engine = create_async_engine(
    _settings.database_url, pool_size=_settings.db_pool_size, pool_pre_ping=True
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
