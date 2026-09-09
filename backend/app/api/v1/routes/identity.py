from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import GuestDep, OptionalUserDep
from app.schemas.identity import Identity
from app.services.colors import color_for

router = APIRouter(tags=["identity"])


@router.get("/identity", response_model=Identity)
async def whoami(user: OptionalUserDep, guest: GuestDep) -> Identity:
    """The current principal, for presence display (name + colour)."""
    if user is not None:
        return Identity(
            kind="user",
            id=str(user.id),
            display_name=user.display_name or user.email,
            color=color_for(str(user.id)),
        )
    if guest is not None:
        return Identity(
            kind="guest",
            id=str(guest.guest_session_id),
            display_name=guest.display_name,
            color=guest.color,
            document_id=str(guest.document_id),
        )
    return Identity(kind="anonymous")
