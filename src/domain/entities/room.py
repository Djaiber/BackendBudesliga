"""Room entity representing a multiplayer game room."""

from dataclasses import dataclass

from .player import Player


@dataclass(frozen=True)
class Room:
    """
    Immutable room entity.

    Represents a multiplayer room where 3-4 players compete together
    in real-time prediction mini-games.
    """

    room_id: str
    players: tuple[Player, ...]
    status: str
    created_at: int  # epoch milliseconds

    # Valid statuses
    WAITING = "waiting"
    ACTIVE = "active"
    MERGING = "merging"
    CLOSED = "closed"

    VALID_STATUSES = {WAITING, ACTIVE, MERGING, CLOSED}

    MIN_PLAYERS = 3
    MAX_PLAYERS = 4

    def __post_init__(self) -> None:
        """Validate room constraints."""
        if not (0 <= len(self.players) <= self.MAX_PLAYERS):
            raise ValueError(f"players count must be 0-{self.MAX_PLAYERS}, got {len(self.players)}")

        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"status must be one of {self.VALID_STATUSES}, got {self.status}")

    def is_mergeable(self) -> bool:
        """
        Check if this room is eligible for merging.

        Returns:
            True if room has fewer than MIN_PLAYERS and is active
        """
        return len(self.players) < self.MIN_PLAYERS and self.status == self.ACTIVE
