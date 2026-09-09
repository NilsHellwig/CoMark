from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.config import settings
from app.core.redis import get_redis


class RateLimiter:
    """Fixed-window limiter backed by Redis. Fails open if Redis is unavailable."""

    def __init__(self, times: int, seconds: int, scope: str) -> None:
        self.times = times
        self.seconds = seconds
        self.scope = scope

    async def __call__(
        self,
        request: Request,
        redis: Redis = Depends(get_redis),
    ) -> None:
        if settings.environment == "test":
            return
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{self.scope}:{client_ip}"
        try:
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, self.seconds)
        except Exception:  # noqa: BLE001 — never block traffic on limiter failure
            return
        if current > self.times:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
            )


auth_rate_limiter = RateLimiter(times=20, seconds=60, scope="auth")
guest_rate_limiter = RateLimiter(times=30, seconds=60, scope="guest")
