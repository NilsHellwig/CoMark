"""Google sign-in — hand-rolled OAuth2 flow.

Two GET routes, both hit by a full browser navigation (no fetch/JSON):

    /authorize  →  redirect the user to Google's consent screen
    /callback   →  Google sends the user back here with a one-time `code`

We roll our own instead of `fastapi_users.get_oauth_router` so the callback can
end with a 302 to the SPA's `/dashboard` and set the same session cookie the
password login uses.
"""

from __future__ import annotations

import logging
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi_users.authentication.strategy.db import DatabaseStrategy

from app.auth.backend import SESSION_COOKIE_NAME, get_database_strategy
from app.auth.oauth import OAUTH_NAME, OAUTH_STATE_COOKIE, google_oauth_client
from app.auth.users import UserManager, get_user_manager
from app.core.config import settings

logger = logging.getLogger("comark.auth.google")

router = APIRouter(prefix="/auth/google", tags=["auth"])

StrategyDep = Annotated[DatabaseStrategy, Depends(get_database_strategy)]
UserManagerDep = Annotated[UserManager, Depends(get_user_manager)]


def _callback_url() -> str:
    # Must be byte-identical in /authorize and /callback, and registered as an
    # "Authorized redirect URI" in the Google Cloud console.
    return f"{settings.public_base_url}/api/v1/auth/google/callback"


@router.get("/authorize")
async def google_authorize() -> RedirectResponse:
    """Step 1 — runs when the user clicks "Continue with Google".

    The frontend button is a plain ``<a href="/api/v1/auth/google/authorize">``,
    so the browser navigates here directly.
    """
    # Google credentials not set → the routes are effectively disabled.
    if google_oauth_client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Google login is not configured")

    # Random anti-CSRF value: goes to Google now and must come back unchanged in
    # /callback, matching the cookie we set below.
    state = secrets.token_urlsafe(24)

    # Build Google's consent URL (client_id + redirect_uri + scopes + state).
    # Scopes = what we ask the user to grant:
    #   openid  → get an ID token / a stable account id ("sub")
    #   email   → read the account's email address
    #   profile → read basic profile (name, picture)
    # These three are "non-sensitive" — no Google app verification needed.
    url = await google_oauth_client.get_authorization_url(
        _callback_url(),
        state=state,
        scope=["openid", "email", "profile"],
    )

    # Why a redirect + cookie and not a JSON response:
    # this endpoint is reached by a *browser navigation* (an <a> click), not a
    # fetch() — so we can only answer with "go here" (302/307) and Set-Cookie
    # headers. The browser then drives the rest: Google → /callback → /dashboard.
    response = RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state,
        # max_age: cookie lifetime in seconds — long enough to finish the consent
        # screen, then it's useless.
        max_age=600,
        # httponly: JavaScript can't read it (document.cookie) — only sent back to
        # the server. Blocks XSS from stealing it.
        httponly=True,
        # samesite="lax": still sent when the user is *navigated* back from
        # google.com to us (top-level GET), but not on cross-site sub-requests.
        samesite="lax",
        # secure: only send over HTTPS. False in local dev (plain http), True in
        # production (see Settings.cookie_secure).
        secure=settings.cookie_secure,
        # path="/": the cookie is attached to every path on this host.
        path="/",
    )
    return response


@router.get("/callback")
async def google_callback(
    request: Request,
    strategy: StrategyDep,
    user_manager: UserManagerDep,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    """Step 2 — Google redirects the user back here after the consent screen.

    On any failure we redirect to ``/login?error=<reason>`` instead of a bare 500,
    so the SPA can show a friendly message.
    """
    if google_oauth_client is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Google login is not configured")

    login_url = f"{settings.public_base_url}/login"

    # User denied consent, or Google didn't send an authorization code.
    if error or not code:
        return RedirectResponse(f"{login_url}?error=google", status_code=302)

    # CSRF check: the `state` in the URL must match the cookie from /authorize.
    expected_state = request.cookies.get(OAUTH_STATE_COOKIE)
    if not expected_state or not state or not secrets.compare_digest(state, expected_state):
        return RedirectResponse(f"{login_url}?error=state", status_code=302)

    try:
        # Exchange the one-time code for a Google access token.
        token = await google_oauth_client.get_access_token(code, _callback_url())

        # Use that token to read the account's Google id + email (People API).
        account_id, account_email = await google_oauth_client.get_id_email(token["access_token"])
        if account_email is None:
            return RedirectResponse(f"{login_url}?error=email", status_code=302)

        # Find or create the CoMark user and link this Google account.
        # associate_by_email → hook onto an existing email/password account;
        # is_verified_by_default → trust Google's verified email.
        user = await user_manager.oauth_callback(
            OAUTH_NAME,
            token["access_token"],
            account_id,
            account_email,
            token.get("expires_at"),
            token.get("refresh_token"),
            request,
            associate_by_email=True,
            is_verified_by_default=True,
        )
        if not user.is_active:
            return RedirectResponse(f"{login_url}?error=inactive", status_code=302)

        # Issue a session (writes an access-token row) — same as password login.
        session_token = await strategy.write_token(user)
    except Exception:
        logger.exception("Google OAuth callback failed")
        return RedirectResponse(f"{login_url}?error=oauth", status_code=302)

    # Land the user in the app, logged in. Same cookie the password login sets:
    # every later request carries it, and the auth dependency looks the token up
    # in the access_token table. (Attributes: see /authorize above.)
    response = RedirectResponse(url=f"{settings.public_base_url}/dashboard", status_code=302)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        max_age=settings.access_token_lifetime_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")  # one-time use, done
    return response
