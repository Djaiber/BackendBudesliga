"""No-op WebSocket broadcaster for Lambdas without a WS endpoint configured."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class NullBroadcaster:
    """Drop-all broadcaster used when WEBSOCKET_API_ENDPOINT is not set."""

    async def send_to_connection(self, connection_id: str, message: dict[str, Any]) -> None:
        logger.warning("NullBroadcaster.send_to_connection: no endpoint configured")

    async def broadcast_to_room(self, room_id: str, message: dict[str, Any]) -> None:
        logger.warning("NullBroadcaster.broadcast_to_room: no endpoint configured")
