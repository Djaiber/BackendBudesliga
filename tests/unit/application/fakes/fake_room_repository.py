"""Fake room repository for testing."""

from src.domain.entities import Player, Room


class FakeRoomRepository:
    """In-memory room repository for testing."""

    def __init__(self) -> None:
        """Initialize fake repository."""
        self.rooms: dict[str, Room] = {}

    async def get(self, room_id: str) -> Room | None:
        """Get room by ID."""
        return self.rooms.get(room_id)

    async def save(self, room: Room) -> None:
        """Save or update room."""
        self.rooms[room.room_id] = room

    async def list_by_status(self, status: str) -> list[Room]:
        """List rooms by status."""
        return [r for r in self.rooms.values() if r.status == status]

    async def add_player(self, room_id: str, player: Player) -> None:
        """Add player to room."""
        room = self.rooms.get(room_id)
        if room is None:
            raise ValueError(f"Room {room_id} not found")
        
        # Create new room with added player
        new_players = list(room.players) + [player]
        self.rooms[room_id] = Room(
            room_id=room.room_id,
            players=tuple(new_players),
            status=room.status,
            created_at=room.created_at,
        )

    async def remove_player(self, room_id: str, user_id: str) -> None:
        """Remove player from room."""
        room = self.rooms.get(room_id)
        if room is None:
            raise ValueError(f"Room {room_id} not found")
        
        # Create new room without the player
        new_players = [p for p in room.players if p.user_id != user_id]
        self.rooms[room_id] = Room(
            room_id=room.room_id,
            players=tuple(new_players),
            status=room.status,
            created_at=room.created_at,
        )

    async def delete(self, room_id: str) -> None:
        """Delete room."""
        self.rooms.pop(room_id, None)

    def clear(self) -> None:
        """Clear all rooms."""
        self.rooms.clear()
