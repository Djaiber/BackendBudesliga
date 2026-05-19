"""Fake WebSocket broadcaster for testing."""

from typing import Any


class FakeWebSocketBroadcaster:
    """In-memory broadcaster that captures sent messages."""

    def __init__(self) -> None:
        """Initialize fake broadcaster."""
        self.sent_to_connection: list[dict[str, Any]] = []
        self.broadcast_to_room_calls: list[dict[str, Any]] = []

    async def send_to_connection(
        self,
        connection_id: str,
        message: dict[str, Any],
    ) -> None:
        """
        Capture message sent to specific connection.

        Args:
            connection_id: WebSocket connection ID
            message: Message to send
        """
        self.sent_to_connection.append({
            "connection_id": connection_id,
            "message": message,
        })

    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict[str, Any],
        exclude_connection_id: str | None = None,
    ) -> None:
        """
        Capture message broadcast to room.

        Args:
            room_id: Room ID to broadcast to
            message: Message to broadcast
            exclude_connection_id: Optional connection to exclude
        """
        self.broadcast_to_room_calls.append({
            "room_id": room_id,
            "message": message,
            "exclude_connection_id": exclude_connection_id,
        })

    def clear(self) -> None:
        """Clear captured messages."""
        self.sent_to_connection.clear()
        self.broadcast_to_room_calls.clear()
