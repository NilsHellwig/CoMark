from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.routes import (
    auth_google,
    collab,
    documents,
    health,
    identity,
    invitations,
    members,
    share_links,
)
from app.auth.backend import bearer_auth_backend, cookie_auth_backend, fastapi_users
from app.core.rate_limit import auth_rate_limiter
from app.schemas.user import UserCreate, UserRead, UserUpdate

api_router = APIRouter()

# --- Authentication ---------------------------------------------------------
_auth_limited = [Depends(auth_rate_limiter)]

api_router.include_router(
    fastapi_users.get_auth_router(cookie_auth_backend, requires_verification=False),
    prefix="/auth/cookie",
    tags=["auth"],
    dependencies=_auth_limited,
)
api_router.include_router(
    fastapi_users.get_auth_router(bearer_auth_backend, requires_verification=False),
    prefix="/auth/bearer",
    tags=["auth"],
    dependencies=_auth_limited,
)
api_router.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
    dependencies=_auth_limited,
)
api_router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
    dependencies=_auth_limited,
)
api_router.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix="/auth",
    tags=["auth"],
)
api_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
api_router.include_router(auth_google.router)

# --- Application -----------------------------------------------------------
api_router.include_router(health.router)
api_router.include_router(identity.router)
api_router.include_router(documents.router)
api_router.include_router(members.router)
api_router.include_router(share_links.router)
api_router.include_router(invitations.router)
api_router.include_router(collab.router)
