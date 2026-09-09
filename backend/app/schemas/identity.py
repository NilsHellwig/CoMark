from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class Identity(BaseModel):
    kind: Literal["user", "guest", "anonymous"]
    id: str | None = None
    display_name: str | None = None
    color: str | None = None
    document_id: str | None = None
