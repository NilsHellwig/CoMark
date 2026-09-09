from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import HTTPConnection

from app.auth.backend import current_user_optional
from app.auth.guest import GuestPrincipal, get_optional_guest
from app.db.models import AccessLevel, Document, User
from app.db.session import get_session
from app.services.permissions import resolve_access, resolve_share_link

SessionDep = Annotated[AsyncSession, Depends(get_session)]
OptionalUserDep = Annotated[User | None, Depends(current_user_optional)]


def get_guest(conn: HTTPConnection) -> GuestPrincipal | None:
    return get_optional_guest(conn)


GuestDep = Annotated[GuestPrincipal | None, Depends(get_guest)]


def get_share_token(
    x_share_token: Annotated[str | None, Header()] = None,
    share_token: Annotated[str | None, Query()] = None,
) -> str | None:
    return x_share_token or share_token


ShareTokenDep = Annotated[str | None, Depends(get_share_token)]


@dataclass(slots=True)
class DocumentContext:
    document: Document
    access_level: AccessLevel
    user: User | None
    guest: GuestPrincipal | None

    @property
    def can_edit(self) -> bool:
        return self.access_level.can_edit

    @property
    def can_manage(self) -> bool:
        return self.access_level.can_manage


async def _context_for(
    document: Document | None,
    *,
    session: AsyncSession,
    user: User | None,
    guest: GuestPrincipal | None,
    share_token: str | None,
) -> DocumentContext:
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    share_link = await resolve_share_link(session, share_token)
    level = await resolve_access(
        session, document=document, user=user, guest=guest, share_link=share_link
    )
    if level is AccessLevel.none:
        # Hide existence from principals without any grant.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    return DocumentContext(document=document, access_level=level, user=user, guest=guest)


async def get_document_context(
    session: SessionDep,
    user: OptionalUserDep,
    guest: GuestDep,
    share_token: ShareTokenDep,
    document_id: uuid.UUID = Path(...),
) -> DocumentContext:
    document = await session.scalar(
        select(Document).where(Document.id == document_id).options(selectinload(Document.owner))
    )
    return await _context_for(
        document, session=session, user=user, guest=guest, share_token=share_token
    )


async def get_document_context_by_slug(
    session: SessionDep,
    user: OptionalUserDep,
    guest: GuestDep,
    share_token: ShareTokenDep,
    slug: str = Path(...),
) -> DocumentContext:
    document = await session.scalar(
        select(Document).where(Document.slug == slug).options(selectinload(Document.owner))
    )
    return await _context_for(
        document, session=session, user=user, guest=guest, share_token=share_token
    )


DocumentContextDep = Annotated[DocumentContext, Depends(get_document_context)]
DocumentContextBySlugDep = Annotated[DocumentContext, Depends(get_document_context_by_slug)]


def require_editor(ctx: DocumentContextDep) -> DocumentContext:
    if not ctx.can_edit:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Editor access required")
    return ctx


def require_owner(ctx: DocumentContextDep) -> DocumentContext:
    if not ctx.can_manage:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Owner access required")
    return ctx


EditorContextDep = Annotated[DocumentContext, Depends(require_editor)]
OwnerContextDep = Annotated[DocumentContext, Depends(require_owner)]
