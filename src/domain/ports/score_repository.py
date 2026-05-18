"""Score repository port - abstract interface for player score storage."""

from typing import Protocol

from src.domain.entities import Player, ScoreDelta


class ScoreRepository(Protocol):
    """
    Abstract repository for player score persistence.

    All methods are async as real implementations will perform I/O.
    """

    async def get_player(self, user_id: str) -> Player | None:
        """
        Retrieve a player by user ID.

        Args:
            user_id: User identifier

        Returns:
            Player if found, None otherwise
        """
        ...

    async def upsert_player(self, player: Player) -> None:
        """
        Insert or update a player.

        Args:
            player: Player to persist
        """
        ...

    async def apply_delta(self, delta: ScoreDelta) -> Player:
        """
        Apply a score delta to a player.

        Args:
            delta: Score delta to apply

        Returns:
            Updated player

        Raises:
            ValueError: If player not found
        """
        ...

    async def leaderboard(self, room_id: str) -> list[Player]:
        """
        Get leaderboard for a room.

        Args:
            room_id: Room identifier

        Returns:
            List of players sorted by score (descending)
        """
        ...
