"""Merge inactive rooms use case."""

from ...domain.entities import Room
from ...domain.ports import Clock, RoomRepository, WebSocketBroadcaster
from ...domain.services import MatchmakerService
from ..dto import player_to_dto


class MergeInactiveRoomsUseCase:
    """
    Use case for merging inactive rooms with low player counts.

    Finds pairs of mergeable rooms and combines them.
    """

    def __init__(
        self,
        room_repo: RoomRepository,
        broadcaster: WebSocketBroadcaster,
        clock: Clock,
    ) -> None:
        self._room_repo = room_repo
        self._broadcaster = broadcaster
        self._clock = clock
        self._matchmaker = MatchmakerService()

    async def execute(self) -> int:
        """
        Execute merge inactive rooms use case.

        Returns:
            Number of merges performed
        """
        # Get all active rooms
        active_rooms = await self._room_repo.list_by_status("active")

        # Find mergeable pairs using MatchmakerService
        pairs = self._matchmaker.find_merge_candidates(active_rooms)

        merged_count = 0
        for room1, room2 in pairs:
            # Merge room2 players into room1
            merged_players = list(room1.players) + list(room2.players)
            merged_room = Room(
                room_id=room1.room_id,
                players=tuple(merged_players),
                status="active",
                created_at=room1.created_at,
            )
            await self._room_repo.save(merged_room)

            # Delete room2
            await self._room_repo.delete(room2.room_id)

            # Broadcast merge notification to both rooms
            message = {
                "type": "room_merged",
                "old_room_id": room2.room_id,
                "new_room_id": room1.room_id,
                "players": [player_to_dto(p) for p in merged_players],
            }

            await self._broadcaster.broadcast_to_room(
                room_id=room2.room_id,
                message=message,
            )
            await self._broadcaster.broadcast_to_room(
                room_id=room1.room_id,
                message=message,
            )

            merged_count += 1

        return merged_count
