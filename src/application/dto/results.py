"""Internal result objects for use case return values."""

from dataclasses import dataclass

from ...domain.entities import Player, Room


@dataclass(frozen=True)
class JoinRoomResult:
    """Result of joining a room."""

    room: Room
    player: Player
    was_merged: bool  # True if player was moved from another room


@dataclass(frozen=True)
class SubmitPredictionResult:
    """Result of submitting a prediction."""

    success: bool
    error: str | None = None


@dataclass(frozen=True)
class CloseWindowResult:
    """Result of closing a prediction window."""

    window_id: str
    correct_answer: str | int
    player_deltas: dict[str, int]  # user_id -> points_earned
