from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum

from app.db.base import Base


class MemberRole(enum.StrEnum):
    """Role stored for collaborators and share links."""

    viewer = "viewer"
    editor = "editor"


class AccessLevel(enum.StrEnum):
    """Computed effective access of a principal on a document (never stored)."""

    none = "none"
    viewer = "viewer"
    editor = "editor"
    owner = "owner"

    @property
    def can_view(self) -> bool:
        return self is not AccessLevel.none

    @property
    def can_edit(self) -> bool:
        return self in (AccessLevel.editor, AccessLevel.owner)

    @property
    def can_manage(self) -> bool:
        return self is AccessLevel.owner


# Single shared PG enum type, associated with the metadata exactly once.
member_role_enum = SAEnum(
    MemberRole,
    name="member_role",
    metadata=Base.metadata,
    values_callable=lambda e: [m.value for m in e],
)
