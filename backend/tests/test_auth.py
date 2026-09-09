from __future__ import annotations

API = "/api/v1"


async def test_register_and_login_cookie(client) -> None:
    email = "cookie-user@example.com"
    reg = await client.post(
        f"{API}/auth/register", json={"email": email, "password": "supersecret123"}
    )
    assert reg.status_code == 201
    assert reg.json()["email"] == email

    login = await client.post(
        f"{API}/auth/cookie/login",
        data={"username": email, "password": "supersecret123"},
    )
    assert login.status_code == 204
    assert "comark_session" in login.cookies

    me = await client.get(f"{API}/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == email


async def test_login_rejects_bad_password(client, make_user) -> None:
    user = await make_user()
    resp = await client.post(
        f"{API}/auth/bearer/login",
        data={"username": user.email, "password": "wrong-password"},
    )
    assert resp.status_code == 400


async def test_logout_revokes_token(client, make_user) -> None:
    user = await make_user()
    me = await user.get("/users/me")
    assert me.status_code == 200

    logout = await client.post(f"{API}/auth/bearer/logout", headers=user.headers)
    assert logout.status_code == 204

    # DatabaseStrategy deletes the token row → it is now invalid.
    me_again = await user.get("/users/me")
    assert me_again.status_code == 401


async def test_display_name_defaults_from_email(client, make_user) -> None:
    user = await make_user()
    me = await user.get("/users/me")
    assert me.json()["display_name"] == user.email.split("@", 1)[0]


async def test_unauthenticated_is_rejected(client) -> None:
    resp = await client.get(f"{API}/users/me")
    assert resp.status_code == 401
