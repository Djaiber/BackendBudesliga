"""Score delta entity representing a scoring event result."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreDelta:
    """
    Immutable score delta entity.

    Represents the result of a scoring calculation, including
    points earned, updated totals, and multipliers applied.
    """

    user_id: str
    points: int  # can be negative for penalties
    new_score: int
    new_streak: int
    new_tier: str
    multiplier_applied: float  # 1.0 | 1.1 | 1.2 | 1.5
