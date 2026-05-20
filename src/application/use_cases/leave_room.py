"""Leave room use case."""

from ...domain.ports import RoomRepository, WebSocketBroadcaster


class LeaveRoomUseCase:
    """Remove a player from their room.

    If the room becomes empty after removal, deletes it.
    Broadcasts PLAYER_LEFT to remaining players.
    """

    def __init__(self, room_repo: RoomRepository, broadcaster: WebSocketBroadcaster) -> None:
        self._room_repo = room_repo
        self._broadcaster = broadcaster

    async def execute(self, user_id: str, room_id: str) -> None:
        room = await self._room_repo.get(room_id)
        if room is None:
            return

        remaining = [p for p in room.players if p.user_id != user_id]

        if not remaining:
            await self._room_repo.delete(room_id)
            return

        await self._room_repo.remove_player(room_id, user_id)

        await self._broadcaster.broadcast_to_room(
            room_id=room_id,
            message={"type": "player_left", "user_id": user_id},
        )
