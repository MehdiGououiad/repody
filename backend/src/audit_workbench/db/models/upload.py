from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from audit_workbench.db.base import Base


class UploadIntent(Base):
    __tablename__ = "upload_intents"
    __table_args__ = (
        Index("ux_upload_intents_storage_key", "storage_key", unique=True),
        Index("ix_upload_intents_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    owner_subject: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
