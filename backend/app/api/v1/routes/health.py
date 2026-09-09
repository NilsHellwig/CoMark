from __future__ import annotations

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core.redis import get_redis

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(session: SessionDep, redis: Redis = Depends(get_redis)) -> dict[str, str]:
    checks: dict[str, str] = {"status": "ok"}
    try:
        await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:  # noqa: BLE001
        checks["database"] = "error"
        checks["status"] = "degraded"
    try:
        await redis.ping()
        checks["redis"] = "ok"
    except Exception:  # noqa: BLE001
        checks["redis"] = "error"
        checks["status"] = "degraded"
    return checks
