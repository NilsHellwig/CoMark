from __future__ import annotations

import contextlib
import json
import secrets
from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Document, MemberRole, ShareLink, User
from app.services.permissions import share_link_is_valid
from app.services.slugs import new_token

_CACHE_TTL_SECONDS = 60
_CACHE_PREFIX = "sharelink:"
_INVALID = "__invalid__"

# Muted, Scandinavian-leaning presence palette.
GUEST_COLORS = (
    "#3B5B6B",
    "#7A6C5D",
    "#4C6B54",
    "#8A5A44",
    "#5C5470",
    "#A08A48",
    "#4A7A82",
    "#9A6A6A",
)


def pick_guest_color() -> str:
    return secrets.choice(GUEST_COLORS)


def build_share_url(token: str) -> str:
    return f"{settings.public_base_url}/s/{token}"


async def create_share_link(
    session: AsyncSession,
    *,
    document: Document,
    role: MemberRole,
    created_by: User,
    expires_in_hours: int | None,
) -> ShareLink:
    expires_at = datetime.now(UTC) + timedelta(hours=expires_in_hours) if expires_in_hours else None
    link = ShareLink(
        document_id=document.id,
        token=new_token(),
        role=role,
        created_by=created_by.id,
        expires_at=expires_at,
    )
    session.add(link)
    await session.flush()
    return link


async def resolve_public_link(session: AsyncSession, redis: Redis, token: str) -> dict | None:
    """Return ``{document_id, slug, title, role, share_link_id}`` for a valid link.

    Cached in Redis for a short window; the cache is busted on revoke.
    """
    cache_key = f"{_CACHE_PREFIX}{token}"
    cached = None
    with contextlib.suppress(Exception):
        cached = await redis.get(cache_key)
    if cached == _INVALID:
        return None
    if cached:
        return json.loads(cached)

    link = await session.scalar(select(ShareLink).where(ShareLink.token == token))
    if link is None or not share_link_is_valid(link):
        with contextlib.suppress(Exception):
            await redis.set(cache_key, _INVALID, ex=_CACHE_TTL_SECONDS)
        return None

    document = await session.get(Document, link.document_id)
    if document is None:
        return None

    payload = {
        "document_id": str(document.id),
        "slug": document.slug,
        "title": document.title,
        "role": link.role.value,
        "share_link_id": str(link.id),
    }
    with contextlib.suppress(Exception):
        await redis.set(cache_key, json.dumps(payload), ex=_CACHE_TTL_SECONDS)
    return payload


async def bust_link_cache(redis: Redis, token: str) -> None:
    with contextlib.suppress(Exception):
        await redis.delete(f"{_CACHE_PREFIX}{token}")
