from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.models.enums import MemberRole, member_role_enum

if TYPE_CHECKING:
    from app.db.models.document import Document
    from app.db.models.user import User


class DocumentMember(TimestampMixin, Base):
    __tablename__ = "document_members"

    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[MemberRole] = mapped_column(member_role_enum, default=MemberRole.editor)

    document: Mapped[Document] = relationship("Document", back_populates="members")
    user: Mapped[User] = relationship("User", lazy="joined")
