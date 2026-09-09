from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import MemberRole


class ShareLinkCreate(BaseModel):
    role: MemberRole = MemberRole.editor
    expires_in_hours: int | None = Field(default=None, ge=1, le=24 * 365)


class ShareLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    token: str
    role: MemberRole
    url: str
    revoked: bool
    created_at: datetime
    expires_at: datetime | None = None


class ShareLinkDocumentBrief(BaseModel):
    slug: str
    title: str


class ShareLinkResolved(BaseModel):
    document: ShareLinkDocumentBrief
    role: MemberRole
    requires_guest_name: bool


class GuestJoin(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)


class GuestJoined(BaseModel):
    document_slug: str
    display_name: str
    color: str
    role: MemberRole
