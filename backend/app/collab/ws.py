from __future__ import annotations

import contextlib
import logging
import uuid

from fastapi import APIRouter, WebSocket
from fastapi_users.authentication.strategy.db import DatabaseStrategy
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from fastapi_users_db_sqlalchemy.access_token import SQLAlchemyAccessTokenDatabase
from pycrdt import Channel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.backend import SESSION_COOKIE_NAME
from app.auth.guest import get_optional_guest
from app.auth.users import UserManager
from app.collab.adapter import FastAPIChannel, ReadOnlyChannel
from app.collab.manager import RoomManager
from app.core.config import settings
from app.db.models import AccessLevel, AccessToken, Document, OAuthAccount, User
from app.db.session import async_session_maker
from app.services.permissions import resolve_access, resolve_share_link

logger = logging.getLogger("comark.collab.ws")

router = APIRouter(tags=["collab"])

# Close codes surfaced to the y-websocket client.
WS_NOT_FOUND = 4404
WS_FORBIDDEN = 4403


async def _authenticate_user(websocket: WebSocket, session: AsyncSession) -> User | None:
    token = websocket.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
    if not token:
        token = websocket.query_params.get("token")
    if not token:
        return None

    strategy: DatabaseStrategy = DatabaseStrategy(
        SQLAlchemyAccessTokenDatabase(session, AccessToken),
        lifetime_seconds=settings.access_token_lifetime_seconds,
    )
    user_manager = UserManager(SQLAlchemyUserDatabase(session, User, OAuthAccount))
    try:
        return await strategy.read_token(token, user_manager)
    except Exception:  # noqa: BLE001
        return None


@router.websocket("/collab/{document_id}")
async def collab_websocket(websocket: WebSocket, document_id: uuid.UUID) -> None:
    async with async_session_maker() as session:
        document = await session.get(Document, document_id)
        if document is None:
            await websocket.close(code=WS_NOT_FOUND)
            return

        user = await _authenticate_user(websocket, session)
        guest = get_optional_guest(websocket)
        share_link = await resolve_share_link(session, websocket.query_params.get("share_token"))
        level = await resolve_access(
            session, document=document, user=user, guest=guest, share_link=share_link
        )

    if level is AccessLevel.none:
        await websocket.close(code=WS_FORBIDDEN)
        return

    await websocket.accept()
    manager: RoomManager = websocket.app.state.rooms
    channel: Channel = FastAPIChannel(websocket, f"/{document_id}")
    if not level.can_edit:
        channel = ReadOnlyChannel(channel)
    try:
        await manager.serve(channel)
    except Exception:  # noqa: BLE001
        logger.exception("collab session crashed for %s", document_id)
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()
