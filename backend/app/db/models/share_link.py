from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPKMixin
from app.db.models.enums import MemberRole, member_role_enum

if TYPE_CHECKING:
    from app.db.models.document import Document


class ShareLink(UUIDPKMixin, TimestampMixin, Base):
    __tablename__ = "share_links"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    role: Mapped[MemberRole] = mapped_column(member_role_enum, default=MemberRole.editor)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked: Mapped[bool] = mapped_column(default=False, server_default="false")

    document: Mapped[Document] = relationship("Document")
