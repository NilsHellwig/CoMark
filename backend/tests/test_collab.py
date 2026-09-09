from __future__ import annotations

import anyio
import pytest
from app.collab.adapter import ReadOnlyChannel, is_doc_mutation
from app.collab.manager import RoomManager
from app.collab.ystore import PostgresYStore
from pycrdt import Doc, Provider, Text

API = "/api/v1"


# --- Unit: read-only message filter --------------------------------------
def test_read_only_filter_blocks_only_mutations() -> None:
    assert is_doc_mutation(bytes([0, 1, 0])) is True  # SYNC_STEP2
    assert is_doc_mutation(bytes([0, 2, 0])) is True  # UPDATE
    assert is_doc_mutation(bytes([0, 0, 0])) is False  # SYNC_STEP1 (state request)
    assert is_doc_mutation(bytes([1, 0])) is False  # AWARENESS
    assert is_doc_mutation(b"") is False


# --- Unit: Postgres-backed store ----------------------------------------
async def test_ystore_persists_and_compacts(owner) -> None:
    doc_meta = (await owner.post("/documents", json={"title": "Y"})).json()
    store = PostgresYStore(f"/{doc_meta['id']}")

    source = Doc()
    source["body"] = text = Text()
    text += "first"
    await store.write(source.get_update())
    text += " second"
    await store.write(source.get_update())

    restored = Doc()
    await store.apply_updates(restored)
    restored["body"] = restored_text = Text()
    assert str(restored_text) == "first second"

    await store.compact(restored)
    rows = [row async for row in store.read()]
    assert len(rows) == 1


# --- In-memory channel pair for the pycrdt client provider ------------
def _channel_pair(path: str) -> tuple[_Endpoint, _Endpoint]:
    c2s_send, c2s_recv = anyio.create_memory_object_stream[bytes](256)
    s2c_send, s2c_recv = anyio.create_memory_object_stream[bytes](256)
    server = _Endpoint(path, s2c_send, c2s_recv)
    client = _Endpoint(path, c2s_send, s2c_recv)
    return server, client


class _Endpoint:
    def __init__(self, path: str, send_stream, recv_stream) -> None:
        self._path = path
        self._send = send_stream
        self._recv = recv_stream

    @property
    def path(self) -> str:
        return self._path

    def __aiter__(self) -> _Endpoint:
        return self

    async def __anext__(self) -> bytes:
        return await self.recv()

    async def recv(self) -> bytes:
        try:
            return await self._recv.receive()
        except (anyio.EndOfStream, anyio.ClosedResourceError) as exc:
            raise StopAsyncIteration from exc

    async def send(self, message: bytes) -> None:
        try:
            await self._send.send(message)
        except (anyio.BrokenResourceError, anyio.ClosedResourceError):
            return


async def _make_document(session_user) -> str:
    doc = (await session_user.post("/documents", json={"title": "Live"})).json()
    return doc["id"]


# --- Integration: rooms via RoomManager ------------------------------
async def test_two_editors_converge(owner) -> None:
    doc_id = await _make_document(owner)
    path = f"/{doc_id}"

    async with RoomManager() as manager, anyio.create_task_group() as tg:
        srv_a, cli_a = _channel_pair(path)
        tg.start_soon(manager.serve, srv_a)

        doc_a = Doc()
        async with Provider(doc_a, cli_a):
            doc_a["body"] = text_a = Text()
            text_a += "hello from A"
            await anyio.sleep(0.3)

            srv_b, cli_b = _channel_pair(path)
            tg.start_soon(manager.serve, srv_b)
            doc_b = Doc()
            async with Provider(doc_b, cli_b):
                await anyio.sleep(0.4)
                doc_b["body"] = text_b = Text()
                assert str(text_b) == "hello from A"

                text_b += " and B"
                await anyio.sleep(0.4)
                assert str(text_a) == "hello from A and B"

        tg.cancel_scope.cancel()


async def test_room_hydrates_from_store(owner) -> None:
    doc_id = await _make_document(owner)
    path = f"/{doc_id}"

    seed = Doc()
    seed["body"] = seed_text = Text()
    seed_text += "persisted content"
    await PostgresYStore(path).write(seed.get_update())

    async with RoomManager() as manager, anyio.create_task_group() as tg:
        srv, cli = _channel_pair(path)
        tg.start_soon(manager.serve, srv)
        doc = Doc()
        async with Provider(doc, cli):
            await anyio.sleep(0.4)
            doc["body"] = text = Text()
            assert str(text) == "persisted content"
        tg.cancel_scope.cancel()


async def test_viewer_edits_are_rejected(owner) -> None:
    doc_id = await _make_document(owner)
    path = f"/{doc_id}"

    async with RoomManager() as manager, anyio.create_task_group() as tg:
        srv_editor, cli_editor = _channel_pair(path)
        tg.start_soon(manager.serve, srv_editor)
        editor_doc = Doc()
        async with Provider(editor_doc, cli_editor):
            editor_doc["body"] = editor_text = Text()
            editor_text += "authoritative"
            await anyio.sleep(0.3)

            srv_viewer, cli_viewer = _channel_pair(path)
            tg.start_soon(manager.serve, ReadOnlyChannel(srv_viewer))
            viewer_doc = Doc()
            async with Provider(viewer_doc, cli_viewer):
                await anyio.sleep(0.4)
                viewer_doc["body"] = viewer_text = Text()
                assert str(viewer_text) == "authoritative"  # viewers still read

                viewer_text += " tampered"
                await anyio.sleep(0.4)
                assert str(editor_text) == "authoritative"  # mutation dropped

        tg.cancel_scope.cancel()


@pytest.mark.parametrize("bad", ["not-a-uuid"])
def test_ystore_rejects_non_uuid_path(bad: str) -> None:
    with pytest.raises(ValueError):
        PostgresYStore(f"/{bad}")


async def test_websocket_route_auth(make_user) -> None:
    """The HTTP WebSocket route accepts an editor and rejects a stranger."""
    from httpx_ws import HTTPXWSException, aconnect_ws

    from tests.conftest import make_live_client

    user = await make_user()
    stranger = await make_user()

    async with make_live_client() as client:
        doc = (
            await client.post(
                f"{API}/documents",
                json={"title": "Private"},
                headers={"Authorization": f"Bearer {user.token}"},
            )
        ).json()

        # Stranger: rejected before the upgrade completes.
        with pytest.raises(HTTPXWSException):
            async with aconnect_ws(
                f"http://testserver{API}/collab/{doc['id']}?token={stranger.token}",
                client=client,
            ):
                pass

        # Owner: connection upgrades and the server sends the initial sync step.
        async with aconnect_ws(
            f"http://testserver{API}/collab/{doc['id']}?token={user.token}",
            client=client,
        ) as ws:
            first = await ws.receive_bytes()
            assert first[0] == 0  # YMessageType.SYNC
