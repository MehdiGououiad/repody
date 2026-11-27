"""Async SQLAlchemy 2.1 engine, sessions, and declarative base for ``repody_core``."""

import enum
import typing
from datetime import datetime
from functools import cache
from typing import Annotated

from sqlalchemy import DateTime, Enum, MetaData, String, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column

from repody_core.settings import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

UtcDateTime = Annotated[datetime, mapped_column(DateTime(timezone=True))]
CreatedAt = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now())]
UpdatedAt = Annotated[
    datetime,
    mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
]


class Base(DeclarativeBase):
    """Base model with explicit naming conventions and strict Literal CHECK constraints."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: typing.ClassVar = {
        str: String(),
        typing.Literal: Enum(enum.Enum, native_enum=False, create_constraint=True, length=None),
    }


@cache
def get_engine() -> AsyncEngine:
    """Create the async engine lazily so schema/tests import cleanly without Postgres."""
    settings = get_settings()
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_size=settings.db_pool_size,
        pool_pre_ping=True,
        connect_args={"server_settings": {"timezone": "UTC"}},
    )


@cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)
