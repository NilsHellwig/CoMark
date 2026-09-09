from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.db.models import MemberRole
from app.schemas.common import UserBrief


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserBrief
    role: MemberRole
    created_at: datetime


class MemberInvite(BaseModel):
    email: EmailStr
    role: MemberRole = MemberRole.editor


class MemberRoleUpdate(BaseModel):
    role: MemberRole


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: MemberRole
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None


class InvitationCreatedOut(BaseModel):
    invitation: InvitationOut
    accept_url: str
    # Populated in dev so you can test the flow without an email server.
    token: str | None = None


class MembersOverview(BaseModel):
    members: list[MemberOut]
    pending_invitations: list[InvitationOut]
