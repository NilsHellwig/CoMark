from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger("comark.email")


async def send_invitation_email(*, to: str, document_title: str, accept_url: str) -> None:
    """Dev backend: log the invitation. Swap for SMTP/provider in production."""
    logger.info(
        "Invitation to collaborate on %r sent to %s — accept at %s",
        document_title,
        to,
        accept_url,
    )
    if settings.environment == "development":
        print(f"[email] invite {to} → {document_title}: {accept_url}")
