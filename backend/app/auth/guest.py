from __future__ import annotations

import uuid
from dataclasses import dataclass

from starlette.requests import HTTPConnection

from app.core.security import InvalidGuestToken, decode_guest_token
from app.db.models import MemberRole

GUEST_COOKIE_NAME = "comark_guest"


@dataclass(frozen=True, slots=True)
class GuestPrincipal:
    guest_session_id: uuid.UUID
    document_id: uuid.UUID
    role: MemberRole
    display_name: str
    color: str


def _extract_token(conn: HTTPConnection) -> str | None:
    token = conn.cookies.get(GUEST_COOKIE_NAME)
    if token:
        return token
    # WebSocket clients (y-websocket) can only pass credentials via the query string.
    return conn.query_params.get("guest_token")


def get_optional_guest(conn: HTTPConnection) -> GuestPrincipal | None:
    token = _extract_token(conn)
    if not token:
        return None
    try:
        payload = decode_guest_token(token)
    except InvalidGuestToken:
        return None
    try:
        return GuestPrincipal(
            guest_session_id=uuid.UUID(payload["sub"]),
            document_id=uuid.UUID(payload["doc"]),
            role=MemberRole(payload["role"]),
            display_name=payload["name"],
            color=payload["color"],
        )
    except (KeyError, ValueError):
        return None
