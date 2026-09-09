from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr


class Message(BaseModel):
    detail: str


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    display_name: str | None = None
