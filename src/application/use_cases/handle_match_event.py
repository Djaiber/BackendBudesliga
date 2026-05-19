"""Handle match event use case."""

from typing import Any

from ...domain.entities import MatchEvent
from ...domain.ports import EventPublisher, RoomRepository, WebSocketBroadcaster
from ..dto import event_to_message


class HandleMatchEventUseCase:
    """
    Use case for handling incoming match events.

    Broadcasts event to all active rooms and publishes to event bus.
    """

    def __init__(
        self,
        room_repo: RoomRepository,
        broadcaster: WebSocketBroadcaster,
        event_publisher: EventPublisher,
    ) -> None:
        self._room_repo = room_repo
        self._broadcaster = broadcaster
        self._event_publisher = event_publisher

    async def execute(self, event: MatchEvent) -> None:
        """
        Execute handle match event use case.

        Args:
            event: Match event to handle
        """
        # Get all active rooms
        active_rooms = await self._room_repo.list_by_status("active")

        # Broadcast to each room — cast TypedDict to dict[str, Any] for port compatibility
        message: dict[str, Any] = dict(event_to_message(event))
        for room in active_rooms:
            await self._broadcaster.broadcast_to_room(
                room_id=room.room_id,
                message=message,
            )

        # Publish to event bus
        await self._event_publisher.publish(
            source="connected-arena.game-engine",
            detail_type="MatchEvent",
            detail={
                "event_id": event.event_id,
                "event_type": event.event_type,
                "minute": event.minute,
                "second": event.second,
                "team": event.team,
                "player": event.player,
            },
        )
