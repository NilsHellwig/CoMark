from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from app.db.models.membership import DocumentMember
    from app.db.models.user import User


class Document(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "documents"

    slug: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Untitled", server_default="Untitled")
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    # Denormalized latest Markdown render (pushed by editor clients) — used for
    # dashboards, search and export without server-side ProseMirror serialization.
    markdown_cache: Mapped[str] = mapped_column(Text, default="", server_default="")
    last_snapshot_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner: Mapped[User] = relationship("User")
    members: Mapped[list[DocumentMember]] = relationship(
        "DocumentMember", back_populates="document", cascade="all, delete-orphan"
    )
