from __future__ import annotations

import os
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
import pytest

# --- Container-backed environment, set up before any `app.*` import ----------
_PG = None
_REDIS = None


def pytest_configure(config: pytest.Config) -> None:  # noqa: ARG001
    global _PG, _REDIS
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer

    _PG = PostgresContainer("postgres:17-alpine", driver="asyncpg")
    _PG.start()
    _REDIS = RedisContainer("redis:8-alpine")
    _REDIS.start()

    os.environ["ENVIRONMENT"] = "test"
    os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)
    os.environ["DATABASE_URL"] = _PG.get_connection_url()
    redis_host = _REDIS.get_container_host_ip()
    redis_port = _REDIS.get_exposed_port(6379)
    os.environ["REDIS_URL"] = f"redis://{redis_host}:{redis_port}/0"
    os.environ["PUBLIC_BASE_URL"] = "http://testserver"
    os.environ["BACKEND_CORS_ORIGINS"] = "http://testserver"


def pytest_unconfigure(config: pytest.Config) -> None:  # noqa: ARG001
    if _REDIS is not None:
        _REDIS.stop()
    if _PG is not None:
        _PG.stop()


# --- Schema + per-test isolation -------------------------------------------
@pytest.fixture(scope="session", autouse=True)
async def _create_schema() -> AsyncIterator[None]:
    import app.db.models  # noqa: F401
    from app.db.base import Base
    from app.db.session import engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_state() -> AsyncIterator[None]:
    from app.core.redis import get_redis_client
    from app.db.base import Base
    from app.db.session import engine
    from sqlalchemy import text

    yield
    tables = ", ".join(f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables))
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    redis = get_redis_client()
    try:
        await redis.flushdb()
    finally:
        await redis.aclose()


# --- HTTP client ----------------------------------------------------------
@pytest.fixture
async def app():
    # A fresh FastAPI app object per test (no server started).
    from app.main import create_app

    return create_app()


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:
    # `ASGITransport` = tell httpx to hand requests straight to the app object
    # in memory, instead of over the network. No server, no port, no socket.
    transport = httpx.ASGITransport(app=app)
    # `base_url` is a dummy host so tests can use relative paths ("/api/v1/...").
    # `async with` closes the client when the test ends.
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        # Hand `c` to the test; execution resumes here once it finishes.
        yield c


@asynccontextmanager
async def make_live_client() -> AsyncIterator[httpx.AsyncClient]:
    """App with a running lifespan (RoomManager started) + WebSocket transport.

    Used as ``async with make_live_client() as client:`` *inside* a test so setup
    and teardown share the test's task (pytest-asyncio + anyio cancel-scope safety).
    """
    from app.main import create_app
    from asgi_lifespan import LifespanManager
    from httpx_ws.transport import ASGIWebSocketTransport

    application = create_app()
    async with LifespanManager(application):
        transport = ASGIWebSocketTransport(application)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c


API = "/api/v1"


class UserSession:
    def __init__(self, client, *, email: str, password: str, user_id: str, token: str):
        self.client = client
        self.email = email
        self.password = password
        self.user_id = user_id
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}

    async def get(self, url, **kw):
        return await self.client.get(f"{API}{url}", headers=self.headers, **kw)

    async def post(self, url, **kw):
        return await self.client.post(f"{API}{url}", headers=self.headers, **kw)

    async def patch(self, url, **kw):
        return await self.client.patch(f"{API}{url}", headers=self.headers, **kw)

    async def delete(self, url, **kw):
        return await self.client.delete(f"{API}{url}", headers=self.headers, **kw)

    async def put(self, url, **kw):
        return await self.client.put(f"{API}{url}", headers=self.headers, **kw)


@pytest.fixture
def make_user(client):
    counter = {"n": 0}

    async def _make(password: str = "supersecret123") -> UserSession:
        counter["n"] += 1
        email = f"user{counter['n']}-{secrets.token_hex(4)}@example.com"
        reg = await client.post(f"{API}/auth/register", json={"email": email, "password": password})
        assert reg.status_code == 201, reg.text
        user_id = reg.json()["id"]
        login = await client.post(
            f"{API}/auth/bearer/login",
            data={"username": email, "password": password},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        return UserSession(client, email=email, password=password, user_id=user_id, token=token)

    return _make


@pytest.fixture
async def owner(make_user) -> UserSession:
    return await make_user()


@pytest.fixture
async def other(make_user) -> UserSession:
    return await make_user()


@pytest.fixture
async def document(owner: UserSession) -> dict:
    resp = await owner.post("/documents", json={"title": "Test Doc"})
    assert resp.status_code == 201, resp.text
    return resp.json()
