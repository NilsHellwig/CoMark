from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import settings

GUEST_TOKEN_AUDIENCE = "comark:guest"
_ALGORITHM = "HS256"


class InvalidGuestToken(Exception):
    pass


def create_guest_token(
    *,
    document_id: uuid.UUID,
    guest_session_id: uuid.UUID,
    role: str,
    display_name: str,
    color: str,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(guest_session_id),
        "aud": GUEST_TOKEN_AUDIENCE,
        "doc": str(document_id),
        "role": role,
        "name": display_name,
        "color": color,
        "iat": now,
        "exp": now + timedelta(seconds=settings.guest_token_lifetime_seconds),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=_ALGORITHM)


def decode_guest_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[_ALGORITHM],
            audience=GUEST_TOKEN_AUDIENCE,
        )
    except jwt.PyJWTError as exc:  # noqa: TRY003
        raise InvalidGuestToken(str(exc)) from exc
