"""Room repository port - abstract interface for room storage."""

from typing import Protocol

from src.domain.entities import Player, Room


class RoomRepository(Protocol):
    """
    Abstract repository for room persistence.

    All methods are async as real implementations will perform I/O.
    """

    async def get(self, room_id: str) -> Room | None:
        """
        Retrieve a room by ID.

        Args:
            room_id: Room identifier

        Returns:
            Room if found, None otherwise
        """
        ...

    async def save(self, room: Room) -> None:
        """
        Save or update a room.

        Args:
            room: Room to persist
        """
        ...

    async def list_by_status(self, status: str) -> list[Room]:
        """
        List all rooms with a given status.

        Args:
            status: Room status to filter by

        Returns:
            List of rooms matching the status
        """
        ...

    async def add_player(self, room_id: str, player: Player) -> Room:
        """
        Add a player to a room.

        Args:
            room_id: Room identifier
            player: Player to add

        Returns:
            Updated room

        Raises:
            ValueError: If room not found or room is full
        """
        ...

    async def remove_player(self, room_id: str, user_id: str) -> Room:
        """
        Remove a player from a room.

        Args:
            room_id: Room identifier
            user_id: User identifier to remove

        Returns:
            Updated room

        Raises:
            ValueError: If room or player not found
        """
        ...

    async def delete(self, room_id: str) -> None:
        """
        Delete a room.

        Args:
            room_id: Room identifier
        """
        ...
