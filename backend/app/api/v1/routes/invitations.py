from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.auth.backend import current_user
from app.db.models import AccessLevel, Document, DocumentMember, Invitation, User
from app.schemas.common import UserBrief
from app.schemas.document import DocumentOut

router = APIRouter(prefix="/invitations", tags=["invitations"])

CurrentUser = Annotated[User, Depends(current_user)]


@router.post("/{token}/accept", response_model=DocumentOut)
async def accept_invitation(token: str, session: SessionDep, user: CurrentUser) -> DocumentOut:
    invitation = await session.scalar(select(Invitation).where(Invitation.token == token))
    if invitation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation not found")

    expires = invitation.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise HTTPException(status.HTTP_410_GONE, "Invitation has expired")

    document = await session.get(Document, invitation.document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document no longer exists")

    level = AccessLevel.owner
    if document.owner_id != user.id:
        member = await session.get(DocumentMember, {"document_id": document.id, "user_id": user.id})
        if member is None:
            member = DocumentMember(document_id=document.id, user_id=user.id, role=invitation.role)
            session.add(member)
        else:
            member.role = invitation.role
        level = AccessLevel.editor if invitation.role.value == "editor" else AccessLevel.viewer

    if invitation.accepted_at is None:
        invitation.accepted_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(document, attribute_names=["owner"])

    return DocumentOut(
        id=document.id,
        slug=document.slug,
        title=document.title,
        owner=UserBrief.model_validate(document.owner),
        created_at=document.created_at,
        updated_at=document.updated_at,
        access_level=level,
    )
