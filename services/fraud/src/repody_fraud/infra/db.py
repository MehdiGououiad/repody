"""Async SQLAlchemy 2.1 engine, pgvector codec hook, and base model."""

import enum
import typing
from datetime import datetime
from functools import cache
from typing import Annotated, Any

from pgvector.asyncpg import register_vector
from sqlalchemy import DateTime, Enum, MetaData, String, event, func
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, mapped_column

from repody_fraud.settings import get_settings

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

UtcDateTime = Annotated[datetime, mapped_column(DateTime(timezone=True))]
CreatedAt = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now())]


class Base(DeclarativeBase):
    """Base ORM model for ``repody_fraud``."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: typing.ClassVar = {
        str: String(),
        typing.Literal: Enum(enum.Enum, native_enum=False, create_constraint=True, length=None),
    }


@cache
def get_engine() -> AsyncEngine:
    """Create the async Postgres + pgvector engine lazily."""
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url.get_secret_value(),
        pool_size=settings.db_pool_size,
        pool_pre_ping=True,
        connect_args={"server_settings": {"timezone": "UTC"}},
    )

    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_conn: Any, _record: Any) -> None:
        dbapi_conn.run_async(register_vector)

    return engine


@cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the shared async session factory."""
    return async_sessionmaker(get_engine(), expire_on_commit=False)
