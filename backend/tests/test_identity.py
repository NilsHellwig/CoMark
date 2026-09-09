from __future__ import annotations

API = "/api/v1"


async def test_identity_anonymous(client) -> None:
    resp = await client.get(f"{API}/identity")
    assert resp.status_code == 200
    assert resp.json()["kind"] == "anonymous"


async def test_identity_user(owner) -> None:
    resp = await owner.get("/identity")
    body = resp.json()
    assert body["kind"] == "user"
    assert body["id"] == owner.user_id
    assert body["color"].startswith("#")


async def test_identity_guest(client, owner) -> None:
    doc = (await owner.post("/documents", json={"title": "G"})).json()
    link = (await owner.post(f"/documents/{doc['id']}/share-links", json={"role": "editor"})).json()
    await client.post(f"{API}/share-links/{link['token']}/guest", json={"display_name": "Robin"})

    resp = await client.get(f"{API}/identity")
    body = resp.json()
    assert body["kind"] == "guest"
    assert body["display_name"] == "Robin"
    assert body["document_id"] == doc["id"]
