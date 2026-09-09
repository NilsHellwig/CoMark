from __future__ import annotations

import anyio
from pycrdt import Channel, YMessageType, YSyncMessageType
from starlette.websockets import WebSocket, WebSocketDisconnect


def is_doc_mutation(message: bytes) -> bool:
    """True for Yjs messages that would change the shared document.

    SYNC_STEP1 (state request) and AWARENESS (presence / cursors) are *not*
    mutations, so viewers still receive content and can broadcast their pointer.
    """
    if len(message) < 2:
        return False
    if message[0] != YMessageType.SYNC:
        return False
    return message[1] in (YSyncMessageType.SYNC_STEP2, YSyncMessageType.SYNC_UPDATE)


class FastAPIChannel:
    """Adapts a Starlette ``WebSocket`` to the pycrdt ``Channel`` protocol."""

    def __init__(self, websocket: WebSocket, path: str) -> None:
        self._ws = websocket
        self._path = path
        self._send_lock = anyio.Lock()

    @property
    def path(self) -> str:
        return self._path

    def __aiter__(self) -> FastAPIChannel:
        return self

    async def __anext__(self) -> bytes:
        return await self.recv()

    async def recv(self) -> bytes:
        try:
            return await self._ws.receive_bytes()
        except (WebSocketDisconnect, RuntimeError, KeyError) as exc:
            raise StopAsyncIteration from exc

    async def send(self, message: bytes) -> None:
        try:
            async with self._send_lock:
                await self._ws.send_bytes(message)
        except (WebSocketDisconnect, RuntimeError):
            # Client is gone; the room will drop this channel on the next read.
            return


class ReadOnlyChannel:
    """Wraps a ``Channel`` and drops inbound document mutations.

    This is the server-side enforcement of the *viewer* role: viewers still
    receive the document and can broadcast awareness (their live cursor), but
    any edit they send never reaches the room's authoritative document.
    """

    def __init__(self, inner: Channel) -> None:
        self._inner = inner

    @property
    def path(self) -> str:
        return self._inner.path

    def __aiter__(self) -> ReadOnlyChannel:
        return self

    async def __anext__(self) -> bytes:
        return await self.recv()

    async def recv(self) -> bytes:
        while True:
            message = await self._inner.recv()
            if not is_doc_mutation(message):
                return message

    async def send(self, message: bytes) -> None:
        await self._inner.send(message)
