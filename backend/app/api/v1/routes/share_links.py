from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from redis.asyncio import Redis
from sqlalchemy import select

from app.api.deps import OwnerContextDep, SessionDep
from app.auth.backend import current_user
from app.auth.guest import GUEST_COOKIE_NAME
from app.core.config import settings
from app.core.rate_limit import guest_rate_limiter
from app.core.redis import get_redis
from app.core.security import create_guest_token
from app.db.models import Document, GuestSession, MemberRole, ShareLink, User
from app.schemas.share import (
    GuestJoin,
    GuestJoined,
    ShareLinkCreate,
    ShareLinkDocumentBrief,
    ShareLinkOut,
    ShareLinkResolved,
)
from app.services.share import (
    build_share_url,
    bust_link_cache,
    create_share_link,
    pick_guest_color,
    resolve_public_link,
)

router = APIRouter(tags=["share-links"])

RedisDep = Annotated[Redis, Depends(get_redis)]
CurrentUser = Annotated[User, Depends(current_user)]


def _to_out(link: ShareLink) -> ShareLinkOut:
    return ShareLinkOut(
        id=link.id,
        token=link.token,
        role=link.role,
        url=build_share_url(link.token),
        revoked=link.revoked,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


@router.get("/documents/{document_id}/share-links", response_model=list[ShareLinkOut])
async def list_share_links(ctx: OwnerContextDep, session: SessionDep) -> list[ShareLinkOut]:
    stmt = (
        select(ShareLink)
        .where(ShareLink.document_id == ctx.document.id)
        .order_by(ShareLink.created_at.desc())
    )
    return [_to_out(link) for link in (await session.scalars(stmt)).all()]


@router.post(
    "/documents/{document_id}/share-links",
    response_model=ShareLinkOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_link(
    payload: ShareLinkCreate, ctx: OwnerContextDep, session: SessionDep
) -> ShareLinkOut:
    assert ctx.user is not None
    link = await create_share_link(
        session,
        document=ctx.document,
        role=payload.role,
        created_by=ctx.user,
        expires_in_hours=payload.expires_in_hours,
    )
    await session.commit()
    await session.refresh(link)
    return _to_out(link)


@router.delete("/share-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_link(
    link_id: uuid.UUID,
    session: SessionDep,
    redis: RedisDep,
    user: CurrentUser,
) -> Response:
    link = await session.get(ShareLink, link_id)
    if link is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    document = await session.get(Document, link.document_id)
    if document is None or document.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Owner access required")
    link.revoked = True
    await session.commit()
    await bust_link_cache(redis, link.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/share-links/{token}",
    response_model=ShareLinkResolved,
    dependencies=[Depends(guest_rate_limiter)],
)
async def resolve_link(token: str, session: SessionDep, redis: RedisDep) -> ShareLinkResolved:
    resolved = await resolve_public_link(session, redis, token)
    if resolved is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This link is invalid or has expired")
    return ShareLinkResolved(
        document=ShareLinkDocumentBrief(slug=resolved["slug"], title=resolved["title"]),
        role=MemberRole(resolved["role"]),
        requires_guest_name=True,
    )


@router.post(
    "/share-links/{token}/guest",
    response_model=GuestJoined,
    dependencies=[Depends(guest_rate_limiter)],
)
async def join_as_guest(
    token: str,
    payload: GuestJoin,
    response: Response,
    session: SessionDep,
    redis: RedisDep,
) -> GuestJoined:
    resolved = await resolve_public_link(session, redis, token)
    if resolved is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This link is invalid or has expired")

    document_id = uuid.UUID(resolved["document_id"])
    role = MemberRole(resolved["role"])
    color = pick_guest_color()

    guest_session = GuestSession(
        document_id=document_id,
        share_link_id=uuid.UUID(resolved["share_link_id"]),
        display_name=payload.display_name.strip(),
        color=color,
        last_seen_at=datetime.now(UTC),
    )
    session.add(guest_session)
    await session.commit()
    await session.refresh(guest_session)

    guest_token = create_guest_token(
        document_id=document_id,
        guest_session_id=guest_session.id,
        role=role.value,
        display_name=guest_session.display_name,
        color=color,
    )
    response.set_cookie(
        GUEST_COOKIE_NAME,
        guest_token,
        max_age=settings.guest_token_lifetime_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    return GuestJoined(
        document_slug=resolved["slug"],
        display_name=guest_session.display_name,
        color=color,
        role=role,
    )
