"""Realtime collaboration WebSocket endpoint (mounted under ``/api/v1``)."""

from app.collab.ws import router as router

__all__ = ["router"]
