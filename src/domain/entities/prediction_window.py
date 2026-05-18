"""Prediction window entity representing a mini-game challenge."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PredictionWindow:
    """
    Immutable prediction window entity.

    Represents a time-limited mini-game where players submit predictions
    about upcoming match events.
    """

    window_id: str
    room_id: str
    game: str
    prompt: str
    opened_at_ms: int
    deadline_ms: int
    options: tuple[str, ...] | None
    status: str

    # Valid game types
    NEXT_GOAL_TIMING = "NEXT_GOAL_TIMING"
    CORNERS_IN_INTERVAL = "CORNERS_IN_INTERVAL"
    GOAL_IN_TIME_WINDOW = "GOAL_IN_TIME_WINDOW"

    VALID_GAMES = {NEXT_GOAL_TIMING, CORNERS_IN_INTERVAL, GOAL_IN_TIME_WINDOW}

    # Valid statuses
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"

    VALID_STATUSES = {OPEN, CLOSED, RESOLVED}

    def __post_init__(self) -> None:
        """Validate prediction window constraints."""
        if self.deadline_ms <= self.opened_at_ms:
            raise ValueError(
                f"deadline_ms ({self.deadline_ms}) must be > opened_at_ms ({self.opened_at_ms})"
            )

        if self.game not in self.VALID_GAMES:
            raise ValueError(f"game must be one of {self.VALID_GAMES}, got {self.game}")

        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"status must be one of {self.VALID_STATUSES}, got {self.status}")

    def is_expired(self, now_ms: int) -> bool:
        """
        Check if the prediction window has expired.

        Args:
            now_ms: Current time in epoch milliseconds

        Returns:
            True if current time is past the deadline
        """
        return now_ms >= self.deadline_ms
