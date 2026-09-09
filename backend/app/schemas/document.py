from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import AccessLevel
from app.schemas.common import UserBrief


class DocumentCreate(BaseModel):
    title: str = Field(default="Untitled", max_length=255)


class DocumentUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class DocumentContentUpdate(BaseModel):
    markdown: str = Field(max_length=2_000_000)


class DocumentContentOut(BaseModel):
    markdown: str
    updated_at: datetime | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    owner: UserBrief
    created_at: datetime
    updated_at: datetime
    access_level: AccessLevel


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    updated_at: datetime
    access_level: AccessLevel
    owner: UserBrief
