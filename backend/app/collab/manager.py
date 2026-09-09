from __future__ import annotations

import anyio
from pycrdt.websocket import WebsocketServer, YRoom
from pycrdt.websocket.websocket_server import exception_logger

from app.collab.ystore import PostgresYStore


class RoomManager(WebsocketServer):
    """A ``WebsocketServer`` where every room is backed by a :class:`PostgresYStore`.

    Rooms are created lazily on first connection, hydrated from the persisted
    update log, and compacted + dropped when the last client disconnects.
    """

    def __init__(self) -> None:
        super().__init__(auto_clean_rooms=True, exception_handler=exception_logger)
        self._create_lock = anyio.Lock()
        self._ystores: dict[str, PostgresYStore] = {}

    async def get_room(self, name: str) -> YRoom:
        if name in self.rooms:
            room = self.rooms[name]
            await self.start_room(room)
            return room

        async with self._create_lock:
            if name in self.rooms:  # lost the race
                room = self.rooms[name]
                await self.start_room(room)
                return room

            ystore = PostgresYStore(name, log=self.log)
            room = YRoom(
                ready=False,
                ystore=ystore,
                log=self.log,
                exception_handler=self.exception_handler,
            )
            self.rooms[name] = room
            self._ystores[name] = ystore
            await self.start_room(room)
            try:
                await ystore.apply_updates(room.ydoc)
            except Exception:  # noqa: BLE001
                self.log.exception("Failed to hydrate room %s from store", name)
            room.ready = True
            return room

    async def delete_room(self, *, name: str | None = None, room: YRoom | None = None) -> None:
        if name is None and room is not None:
            name = self.get_room_name(room)
        assert name is not None
        target = room or self.rooms.get(name)
        ystore = self._ystores.pop(name, None)
        if ystore is not None and target is not None:
            try:
                await ystore.compact(target.ydoc)
            except Exception:  # noqa: BLE001
                self.log.exception("Failed to compact room %s", name)
        await super().delete_room(name=name)
