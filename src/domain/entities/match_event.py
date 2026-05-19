"""Match event entity representing a single event during a football match."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MatchEvent:
    """
    Immutable match event from the replay data.

    Represents a single event (pass, shot, goal, etc.) that occurred
    during a football match at a specific time.
    """

    event_id: str
    minute: int
    second: int
    event_type: str
    team: str
    player: str | None
    x_position: float | None
    y_position: float | None
    metadata: dict[str, Any]

    # Valid event types
    VALID_EVENT_TYPES = {
        "PASS",
        "SHOT",
        "GOAL",
        "CORNER_KICK",
        "FOUL",
        "YELLOW",
        "RED",
        "SUB",
        "THROW_IN",
        "GOAL_KICK",
        "FREE_KICK",
        "TACKLING_GAME",
        "CAUTION",
        "OTHER_BALL_ACTION",
        "FINAL_WHISTLE",
        "KICK_OFF",
        "CROSS",
        "PLAY",
        "EVENT",
        "OTHER",
    }

    def __post_init__(self) -> None:
        """Validate match event constraints."""
        if not (0 <= self.minute <= 120):
            raise ValueError(f"minute must be 0-120, got {self.minute}")

        if not (0 <= self.second <= 59):
            raise ValueError(f"second must be 0-59, got {self.second}")

        if self.event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(
                f"event_type must be one of {self.VALID_EVENT_TYPES}, got {self.event_type}"
            )
