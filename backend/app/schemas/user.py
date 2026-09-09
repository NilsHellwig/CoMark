from __future__ import annotations

import uuid
from datetime import datetime

from fastapi_users import schemas
from pydantic import Field


class UserRead(schemas.BaseUser[uuid.UUID]):
    display_name: str | None = None
    created_at: datetime


class UserCreate(schemas.BaseUserCreate):
    display_name: str | None = Field(default=None, max_length=120)


class UserUpdate(schemas.BaseUserUpdate):
    display_name: str | None = Field(default=None, max_length=120)
