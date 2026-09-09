from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

_engine_kwargs: dict = {"pool_pre_ping": True, "echo": False}
if settings.environment == "test":
    # Fresh connection per checkout — avoids cross-event-loop pool reuse in tests.
    _engine_kwargs = {"poolclass": NullPool, "echo": False}

# TLS for managed Postgres (Neon etc.); empty for a local/compose database.
if settings.database_connect_args:
    _engine_kwargs["connect_args"] = settings.database_connect_args

engine: AsyncEngine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        yield session
