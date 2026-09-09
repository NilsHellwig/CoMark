from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import OwnerContextDep, SessionDep
from app.core.config import settings
from app.db.models import Document, DocumentMember, Invitation, MemberRole, User
from app.schemas.common import UserBrief
from app.schemas.member import (
    InvitationCreatedOut,
    InvitationOut,
    MemberInvite,
    MemberOut,
    MemberRoleUpdate,
    MembersOverview,
)
from app.services.email import send_invitation_email
from app.services.slugs import new_token

router = APIRouter(prefix="/documents/{document_id}/members", tags=["members"])

_INVITATION_TTL = timedelta(days=14)


@router.get("", response_model=MembersOverview)
async def list_members(ctx: OwnerContextDep, session: SessionDep) -> MembersOverview:
    members_stmt = (
        select(DocumentMember)
        .where(DocumentMember.document_id == ctx.document.id)
        .order_by(DocumentMember.created_at)
    )
    members = (await session.scalars(members_stmt)).all()

    owner = await session.get(User, ctx.document.owner_id)
    member_out = (
        [
            MemberOut(
                user=UserBrief.model_validate(owner),
                role=MemberRole.editor,
                created_at=ctx.document.created_at,
            )
        ]
        if owner
        else []
    )
    member_out += [
        MemberOut(user=UserBrief.model_validate(m.user), role=m.role, created_at=m.created_at)
        for m in members
    ]

    pending_stmt = (
        select(Invitation)
        .where(
            Invitation.document_id == ctx.document.id,
            Invitation.accepted_at.is_(None),
        )
        .order_by(Invitation.created_at)
    )
    pending = (await session.scalars(pending_stmt)).all()
    return MembersOverview(
        members=member_out,
        pending_invitations=[InvitationOut.model_validate(i) for i in pending],
    )


@router.post("", response_model=InvitationCreatedOut, status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: MemberInvite, ctx: OwnerContextDep, session: SessionDep
) -> InvitationCreatedOut:
    email = payload.email.lower()
    document: Document = ctx.document

    existing_user = await session.scalar(
        select(User).where(User.email == email)  # type: ignore[arg-type]
    )
    if existing_user is not None:
        if existing_user.id == document.owner_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "That user owns this document")
        member = await session.get(
            DocumentMember,
            {"document_id": document.id, "user_id": existing_user.id},
        )
        if member is None:
            member = DocumentMember(
                document_id=document.id, user_id=existing_user.id, role=payload.role
            )
            session.add(member)
        else:
            member.role = payload.role
        await session.flush()

    now = datetime.now(UTC)
    invitation = Invitation(
        document_id=document.id,
        email=email,
        role=payload.role,
        token=new_token(),
        invited_by=ctx.user.id if ctx.user else document.owner_id,
        expires_at=now + _INVITATION_TTL,
        accepted_at=now if existing_user is not None else None,
    )
    session.add(invitation)
    await session.commit()
    await session.refresh(invitation)

    accept_url = f"{settings.public_base_url}/invitations/{invitation.token}"
    if existing_user is None:
        await send_invitation_email(to=email, document_title=document.title, accept_url=accept_url)

    return InvitationCreatedOut(
        invitation=InvitationOut.model_validate(invitation),
        accept_url=accept_url,
        token=invitation.token if settings.environment != "production" else None,
    )


@router.patch("/{user_id}", response_model=MemberOut)
async def update_member_role(
    user_id: uuid.UUID,
    payload: MemberRoleUpdate,
    ctx: OwnerContextDep,
    session: SessionDep,
) -> MemberOut:
    member = await session.get(DocumentMember, {"document_id": ctx.document.id, "user_id": user_id})
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not a collaborator")
    member.role = payload.role
    await session.commit()
    await session.refresh(member, attribute_names=["user"])
    return MemberOut(
        user=UserBrief.model_validate(member.user),
        role=member.role,
        created_at=member.created_at,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(user_id: uuid.UUID, ctx: OwnerContextDep, session: SessionDep) -> Response:
    member = await session.get(DocumentMember, {"document_id": ctx.document.id, "user_id": user_id})
    if member is not None:
        await session.delete(member)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
