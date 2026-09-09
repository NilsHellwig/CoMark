from __future__ import annotations

import pytest


@pytest.fixture
async def doc(owner) -> dict:
    return (await owner.post("/documents", json={"title": "Shared"})).json()


async def test_invite_existing_user_grants_membership(owner, other, doc) -> None:
    resp = await owner.post(
        f"/documents/{doc['id']}/members",
        json={"email": other.email, "role": "editor"},
    )
    assert resp.status_code == 201
    assert resp.json()["invitation"]["accepted_at"] is not None

    got = await other.get(f"/documents/{doc['id']}")
    assert got.status_code == 200
    assert got.json()["access_level"] == "editor"

    assert doc["id"] in {d["id"] for d in (await other.get("/documents")).json()}


async def test_viewer_cannot_edit(owner, other, doc) -> None:
    await owner.post(
        f"/documents/{doc['id']}/members",
        json={"email": other.email, "role": "viewer"},
    )
    got = await other.get(f"/documents/{doc['id']}")
    assert got.json()["access_level"] == "viewer"

    patched = await other.patch(f"/documents/{doc['id']}", json={"title": "hijack"})
    assert patched.status_code == 403

    put = await other.put(f"/documents/{doc['id']}/content", json={"markdown": "nope"})
    assert put.status_code == 403


async def test_only_owner_manages_members_and_deletes(owner, other, doc) -> None:
    await owner.post(
        f"/documents/{doc['id']}/members",
        json={"email": other.email, "role": "editor"},
    )
    assert (await other.get(f"/documents/{doc['id']}/members")).status_code == 403
    assert (await other.delete(f"/documents/{doc['id']}")).status_code == 403
    assert (await owner.delete(f"/documents/{doc['id']}")).status_code == 204


async def test_role_change_and_removal(owner, other, doc) -> None:
    await owner.post(
        f"/documents/{doc['id']}/members",
        json={"email": other.email, "role": "editor"},
    )
    downgrade = await owner.patch(
        f"/documents/{doc['id']}/members/{other.user_id}", json={"role": "viewer"}
    )
    assert downgrade.status_code == 200
    assert downgrade.json()["role"] == "viewer"

    removed = await owner.delete(f"/documents/{doc['id']}/members/{other.user_id}")
    assert removed.status_code == 204
    assert (await other.get(f"/documents/{doc['id']}")).status_code == 404


async def test_invite_new_email_creates_pending_invitation(owner, doc, make_user) -> None:
    resp = await owner.post(
        f"/documents/{doc['id']}/members",
        json={"email": "newcomer@example.com", "role": "editor"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["invitation"]["accepted_at"] is None
    token = body["token"]
    assert token

    overview = await owner.get(f"/documents/{doc['id']}/members")
    assert overview.json()["pending_invitations"][0]["email"] == "newcomer@example.com"

    # A real user accepts it.
    newcomer = await make_user()
    accept = await newcomer.post(f"/invitations/{token}/accept")
    assert accept.status_code == 200
    assert accept.json()["access_level"] == "editor"
