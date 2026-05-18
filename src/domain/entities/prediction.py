"""Prediction entity representing a player's submission for a mini-game."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Prediction:
    """
    Immutable prediction entity.

    Represents a player's submitted answer to a prediction window challenge.
    The value type depends on the game type (string or integer).
    """

    window_id: str
    user_id: str
    value: str | int
    submitted_at_ms: int
