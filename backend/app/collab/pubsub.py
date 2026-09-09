"""Redis fan-out bridge for running the collaboration engine across workers.

The default deployment runs a **single** Uvicorn worker, where rooms live in
process memory and no bridge is needed. To scale horizontally, set
``COLLAB_REDIS_BRIDGE=true`` and implement :func:`attach_bridge` to:

  * subscribe to ``comark:room:{path}`` and apply remote Yjs / awareness updates
    to the local :class:`~pycrdt.websocket.YRoom`;
  * publish local ``ydoc`` updates and awareness changes to the same channel.

Keep the persisted update log (``PostgresYStore``) as the single source of truth;
the bridge only mirrors live traffic between instances.
"""

from __future__ import annotations

from app.collab.manager import RoomManager
from app.core.config import settings


async def attach_bridge(manager: RoomManager) -> None:  # pragma: no cover - scaffold
    if not settings.collab_redis_bridge:
        return
    raise NotImplementedError(
        "Multi-worker collab bridge is not implemented yet — run a single worker "
        "or contribute an implementation here."
    )
