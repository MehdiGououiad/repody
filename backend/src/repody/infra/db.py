"""Async SQLAlchemy engine, sessions, and the declarative base the tables share."""

import enum
import typing
from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, Enum, MetaData, String, func
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, mapped_column

from repody.settings import get_settings

# Constraint names Alembic can rely on (https://alembic.sqlalchemy.org/en/latest/naming.html).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",  # the CHECK of a Literal column
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

UtcDateTime = Annotated[datetime, mapped_column(DateTime(timezone=True))]
CreatedAt = Annotated[datetime, mapped_column(DateTime(timezone=True), server_default=func.now())]
UpdatedAt = Annotated[
    datetime, mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
]


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Text columns have no length limit (the API bounds what users type); a Literal column is a
    # VARCHAR with a CHECK listing its values, named ck_<table>_<column>. SQLAlchemy docs:
    # "Using Python Enum or pep-586 Literal types in the type map".
    type_annotation_map: typing.ClassVar = {
        str: String(),
        typing.Literal: Enum(enum.Enum, native_enum=False, create_constraint=True, length=None),
    }


_settings = get_settings()
# Sessions run in UTC so `date(created_at)` groups by the same days the code computes.
engine = create_async_engine(
    _settings.database_url.get_secret_value(),
    pool_size=_settings.db_pool_size,
    pool_pre_ping=True,
    connect_args={"server_settings": {"timezone": "UTC"}},
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
