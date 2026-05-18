"""Tier service for calculating player tiers based on experience points."""


class TierService:
    """
    Service for determining player tier based on accumulated experience (score).

    Tier thresholds:
    - Dummies: 0-400
    - Enthusiast: 401-700
    - Amateur: 701-900
    - Savvy: 901-1200+
    """

    DUMMIES = "Dummies"
    ENTHUSIAST = "Enthusiast"
    AMATEUR = "Amateur"
    SAVVY = "Savvy"

    def get_tier(self, exp: int) -> str:
        """
        Calculate tier based on experience points.

        Args:
            exp: Experience points (score)

        Returns:
            Tier name

        Raises:
            ValueError: If exp is negative
        """
        if exp < 0:
            raise ValueError(f"exp must be >= 0, got {exp}")

        if exp <= 400:
            return self.DUMMIES
        elif exp <= 700:
            return self.ENTHUSIAST
        elif exp <= 900:
            return self.AMATEUR
        else:
            return self.SAVVY
