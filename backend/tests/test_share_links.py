from __future__ import annotations

import pytest

API = "/api/v1"


@pytest.fixture
async def doc(owner) -> dict:
    return (await owner.post("/documents", json={"title": "Linkable"})).json()


async def test_create_list_and_revoke(owner, doc) -> None:
    created = await owner.post(f"/documents/{doc['id']}/share-links", json={"role": "editor"})
    assert created.status_code == 201
    link = created.json()
    assert link["role"] == "editor"
    assert link["url"].endswith(f"/s/{link['token']}")

    listing = await owner.get(f"/documents/{doc['id']}/share-links")
    assert [x["id"] for x in listing.json()] == [link["id"]]

    revoke = await owner.delete(f"/share-links/{link['id']}")
    assert revoke.status_code == 204

    resolved = await owner.client.get(f"{API}/share-links/{link['token']}")
    assert resolved.status_code == 404


async def test_public_resolve(owner, doc) -> None:
    link = (await owner.post(f"/documents/{doc['id']}/share-links", json={"role": "viewer"})).json()

    resolved = await owner.client.get(f"{API}/share-links/{link['token']}")
    assert resolved.status_code == 200
    body = resolved.json()
    assert body["document"]["slug"] == doc["slug"]
    assert body["role"] == "viewer"
    assert body["requires_guest_name"] is True


async def test_guest_join_grants_scoped_access(client, owner, doc) -> None:
    link = (await owner.post(f"/documents/{doc['id']}/share-links", json={"role": "editor"})).json()

    join = await client.post(
        f"{API}/share-links/{link['token']}/guest", json={"display_name": "Sam"}
    )
    assert join.status_code == 200
    assert join.json()["document_slug"] == doc["slug"]
    assert "comark_guest" in client.cookies

    # The guest cookie now authorises document reads.
    as_guest = await client.get(f"{API}/documents/{doc['id']}")
    assert as_guest.status_code == 200
    assert as_guest.json()["access_level"] == "editor"


async def test_invalid_token_is_404(client) -> None:
    resp = await client.get(f"{API}/share-links/does-not-exist")
    assert resp.status_code == 404


async def test_non_owner_cannot_create_link(other, doc) -> None:
    resp = await other.post(f"/documents/{doc['id']}/share-links", json={"role": "editor"})
    assert resp.status_code == 404  # doc existence hidden from stranger
