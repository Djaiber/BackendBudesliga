"""WebSocket broadcaster port - abstract interface for WebSocket messaging."""

from typing import Any, Protocol


class WebSocketBroadcaster(Protocol):
    """
    Abstract broadcaster for WebSocket messages.

    All methods are async as real implementations will perform I/O.
    """

    async def send_to_connection(self, connection_id: str, message: dict[str, Any]) -> None:
        """
        Send a message to a specific WebSocket connection.

        Args:
            connection_id: WebSocket connection identifier
            message: Message payload to send
        """
        ...

    async def broadcast_to_room(self, room_id: str, message: dict[str, Any]) -> None:
        """
        Broadcast a message to all connections in a room.

        Args:
            room_id: Room identifier
            message: Message payload to broadcast
        """
        ...
