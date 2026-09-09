from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from logging import Logger, getLogger

from pycrdt import Doc
from pycrdt.store import BaseYStore
from sqlalchemy import delete, select

from app.db.models import YjsUpdate
from app.db.session import async_session_maker


class PostgresYStore(BaseYStore):
    """Persists a room's Yjs update stream to the ``yjs_updates`` table.

    The append log is squashed to a single row via :meth:`compact` when the last
    client leaves the room.
    """

    def __init__(
        self,
        path: str,
        metadata_callback: Callable[[], Awaitable[bytes] | bytes] | None = None,
        log: Logger | None = None,
    ) -> None:
        self.path = path
        self.document_id = uuid.UUID(path.strip("/"))
        self.metadata_callback = metadata_callback
        self.log = log or getLogger("comark.collab.ystore")

    async def write(self, data: bytes) -> None:
        async with async_session_maker() as session:
            session.add(YjsUpdate(document_id=self.document_id, data=data))
            await session.commit()

    async def read(self) -> AsyncIterator[tuple[bytes, bytes, float]]:
        async with async_session_maker() as session:
            stmt = (
                select(YjsUpdate)
                .where(YjsUpdate.document_id == self.document_id)
                .order_by(YjsUpdate.id)
            )
            for row in (await session.scalars(stmt)).all():
                yield row.data, b"", row.created_at.timestamp()

    async def compact(self, ydoc: Doc) -> None:
        """Replace the append log with a single squashed update of the full state."""
        squashed = ydoc.get_update()
        async with async_session_maker() as session:
            await session.execute(
                delete(YjsUpdate).where(YjsUpdate.document_id == self.document_id)
            )
            session.add(YjsUpdate(document_id=self.document_id, data=squashed))
            await session.commit()
        self.log.debug("Compacted yjs_updates for %s", self.document_id)
