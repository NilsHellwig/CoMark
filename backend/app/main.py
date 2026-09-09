from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app.api.v1.router import api_router
from app.collab.manager import RoomManager
from app.collab.pubsub import attach_bridge
from app.core.config import settings
from app.core.redis import close_redis_pool

logging.basicConfig(
    level=logging.INFO if settings.environment != "development" else logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logging.getLogger("pycrdt").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager = RoomManager()
    await manager.__aenter__()
    app.state.rooms = manager
    await attach_bridge(manager)
    try:
        yield
    finally:
        await manager.__aexit__(None, None, None)
        await close_redis_pool()


def _operation_id(route: APIRoute) -> str:
    """Short, stable operation ids → clean generated TypeScript SDK names."""
    return route.operation_id or route.name


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        summary="CoMark — collaborative Markdown editor: REST API + realtime engine.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        generate_unique_id_function=_operation_id,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    # include_in_schema = False → don't show in OpenAPI docs
    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.project_name,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_app()
