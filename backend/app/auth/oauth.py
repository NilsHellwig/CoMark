from __future__ import annotations

from httpx_oauth.clients.google import GoogleOAuth2

from app.core.config import settings

google_oauth_client: GoogleOAuth2 | None = (
    GoogleOAuth2(settings.google_oauth_client_id, settings.google_oauth_client_secret)
    if settings.google_oauth_enabled
    else None
)

OAUTH_NAME = "google"
OAUTH_STATE_COOKIE = "comark_oauth_state"
