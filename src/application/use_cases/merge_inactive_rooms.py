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
        """
        Initialize use case with dependencies.

        Args:
            room_repo: Room repository port
            broadcaster: WebSocket broadcaster port
            clock: Clock port
        """
        self._room_repo = room_repo
        self._broadcaster = broadcaster
        self._clock = clock

    async def execute(self) -> int:
        """
        Execute merge inactive rooms use case.

        Returns:
            Number of rooms merged
        """
        # Get all active rooms
        active_rooms = await self._room_repo.list_by_status("active")
        
        # Find mergeable rooms
        mergeable_rooms = [r for r in active_rooms if r.is_mergeable()]
        
        # Pair up rooms
        merged_count = 0
        i = 0
        while i < len(mergeable_rooms) - 1:
            room1 = mergeable_rooms[i]
            room2 = mergeable_rooms[i + 1]
            
            # Check if they can be merged
            pair = MatchmakerService.find_mergeable_pair([room1, room2])
            if pair is not None:
                # Merge room2 into room1
                merged_players = list(room1.players) + list(room2.players)
                merged_room = Room(
                    room_id=room1.room_id,
                    players=tuple(merged_players),
                    status="active",
                    created_at_ms=room1.created_at_ms,
                )
                await self._room_repo.save(merged_room)
                
                # Delete room2
                await self._room_repo.delete(room2.room_id)
                
                # Broadcast merge to both rooms
                message = {
                    "type": "room_merged",
                    "old_room_id": room2.room_id,
                    "new_room_id": room1.room_id,
                    "players": [player_to_dto(p) for p in merged_players],
                }
                
                # Broadcast to old room2 players
                await self._broadcaster.broadcast_to_room(
                    room_id=room2.room_id,
                    message=message,
                )
                
                # Broadcast to room1 players
                await self._broadcaster.broadcast_to_room(
                    room_id=room1.room_id,
                    message=message,
                )
                
                merged_count += 1
                i += 2  # Skip both merged rooms
            else:
                i += 1  # Try next pair
        
        return merged_count
