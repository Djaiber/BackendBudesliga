"""Player entity representing a fan in the Connected Arena game."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Player:
    """
    Immutable player entity.

    Represents a fan participating in the real-time prediction game
    with their current score, tier, and streak.
    """

    user_id: str
    name: str
    score: int
    tier: str
    streak: int

    # Valid tiers
    DUMMIES = "Dummies"
    ENTHUSIAST = "Enthusiast"
    AMATEUR = "Amateur"
    SAVVY = "Savvy"

    VALID_TIERS = {DUMMIES, ENTHUSIAST, AMATEUR, SAVVY}

    def __post_init__(self) -> None:
        """Validate player constraints."""
        if self.score < 0:
            raise ValueError(f"score must be >= 0, got {self.score}")

        if self.streak < 0:
            raise ValueError(f"streak must be >= 0, got {self.streak}")

        if self.tier not in self.VALID_TIERS:
            raise ValueError(f"tier must be one of {self.VALID_TIERS}, got {self.tier}")
