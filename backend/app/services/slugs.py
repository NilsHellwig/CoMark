from __future__ import annotations

import secrets

from slugify import slugify
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Document

_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"


def random_suffix(length: int = 6) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


def new_token(nbytes: int = 24) -> str:
    """URL-safe opaque token for share links and invitations."""
    return secrets.token_urlsafe(nbytes)


async def unique_document_slug(session: AsyncSession, title: str) -> str:
    base = slugify(title or "untitled", max_length=16) or "doc"
    for _ in range(6):
        candidate = f"{base}-{random_suffix()}"
        exists = await session.scalar(select(Document.id).where(Document.slug == candidate))
        if exists is None:
            return candidate
    return f"{base}-{random_suffix(10)}"
