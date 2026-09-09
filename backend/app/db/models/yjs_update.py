from __future__ import annotations

import uuid

from sqlalchemy import BigInteger, ForeignKey, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class YjsUpdate(TimestampMixin, Base):
    """Append-only Yjs update log — the source of truth for document content.

    Rebuilt into a live ``pycrdt.Doc`` when a room opens; compacted into a single
    squashed row when the last client leaves.
    """

    __tablename__ = "yjs_updates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    data: Mapped[bytes] = mapped_column(LargeBinary)
