from __future__ import annotations


async def test_create_list_and_get(owner) -> None:
    created = await owner.post("/documents", json={"title": "My Notes"})
    assert created.status_code == 201
    doc = created.json()
    assert doc["title"] == "My Notes"
    assert doc["access_level"] == "owner"
    assert doc["slug"]

    listing = await owner.get("/documents")
    assert listing.status_code == 200
    assert [d["id"] for d in listing.json()] == [doc["id"]]

    by_id = await owner.get(f"/documents/{doc['id']}")
    assert by_id.status_code == 200
    by_slug = await owner.get(f"/documents/by-slug/{doc['slug']}")
    assert by_slug.status_code == 200
    assert by_slug.json()["id"] == doc["id"]


async def test_rename_and_delete(owner) -> None:
    doc = (await owner.post("/documents", json={"title": "Draft"})).json()

    renamed = await owner.patch(f"/documents/{doc['id']}", json={"title": "Final"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Final"

    deleted = await owner.delete(f"/documents/{doc['id']}")
    assert deleted.status_code == 204
    assert (await owner.get(f"/documents/{doc['id']}")).status_code == 404


async def test_content_roundtrip_and_export(owner) -> None:
    doc = (await owner.post("/documents", json={"title": "Content"})).json()

    put = await owner.put(f"/documents/{doc['id']}/content", json={"markdown": "# Hello\n\nworld"})
    assert put.status_code == 200

    got = await owner.get(f"/documents/{doc['id']}/content")
    assert got.json()["markdown"] == "# Hello\n\nworld"

    export = await owner.get(f"/documents/{doc['id']}/export")
    assert export.status_code == 200
    assert export.text == "# Hello\n\nworld"
    assert "attachment" in export.headers["content-disposition"]


async def test_stranger_cannot_see_document(owner, other) -> None:
    doc = (await owner.post("/documents", json={"title": "Secret"})).json()
    resp = await other.get(f"/documents/{doc['id']}")
    assert resp.status_code == 404  # existence hidden


async def test_create_requires_auth(client) -> None:
    resp = await client.post("/api/v1/documents", json={"title": "x"})
    assert resp.status_code == 401
