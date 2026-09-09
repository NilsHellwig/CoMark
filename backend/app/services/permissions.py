from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.guest import GuestPrincipal
from app.db.models import (
    AccessLevel,
    Document,
    DocumentMember,
    MemberRole,
    ShareLink,
    User,
)

_ROLE_TO_LEVEL = {
    MemberRole.viewer: AccessLevel.viewer,
    MemberRole.editor: AccessLevel.editor,
}
_LEVEL_ORDER = {
    AccessLevel.none: 0,
    AccessLevel.viewer: 1,
    AccessLevel.editor: 2,
    AccessLevel.owner: 3,
}


def _best(a: AccessLevel, b: AccessLevel) -> AccessLevel:
    return a if _LEVEL_ORDER[a] >= _LEVEL_ORDER[b] else b


def share_link_is_valid(link: ShareLink) -> bool:
    if link.revoked:
        return False
    if link.expires_at is not None:
        expires = link.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < datetime.now(UTC):
            return False
    return True


async def resolve_share_link(session: AsyncSession, token: str | None) -> ShareLink | None:
    if not token:
        return None
    link = await session.scalar(select(ShareLink).where(ShareLink.token == token))
    if link is None or not share_link_is_valid(link):
        return None
    return link


async def resolve_access(
    session: AsyncSession,
    *,
    document: Document,
    user: User | None = None,
    guest: GuestPrincipal | None = None,
    share_link: ShareLink | None = None,
) -> AccessLevel:
    """Effective access level of a principal on ``document`` (highest of all grants)."""
    level = AccessLevel.none

    if user is not None:
        if document.owner_id == user.id:
            return AccessLevel.owner
        member = await session.get(DocumentMember, {"document_id": document.id, "user_id": user.id})
        if member is not None:
            level = _best(level, _ROLE_TO_LEVEL[member.role])

    if guest is not None and guest.document_id == document.id:
        level = _best(level, _ROLE_TO_LEVEL[guest.role])

    if share_link is not None and share_link.document_id == document.id:
        level = _best(level, _ROLE_TO_LEVEL[share_link.role])

    return level
