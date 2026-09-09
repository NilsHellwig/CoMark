from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as redis

from app.core.config import settings

_pool: redis.ConnectionPool = redis.ConnectionPool.from_url(
    settings.redis_url, decode_responses=True, max_connections=32
)


def get_redis_client() -> redis.Redis:
    return redis.Redis(connection_pool=_pool)


async def get_redis() -> AsyncGenerator[redis.Redis]:
    client = get_redis_client()
    try:
        yield client
    finally:
        await client.aclose()


async def close_redis_pool() -> None:
    await _pool.aclose()
