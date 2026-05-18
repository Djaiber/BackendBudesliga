"""Scoring service for calculating points from predictions."""


class ScoringService:
    """
    Service for calculating points earned from predictions.

    Scoring rules:
    - Exact prediction: 100 points
    - Closest non-exact: 50, 30, 20, 10 (ranks 2-5)
    - No response: -10 penalty
    - Speed multiplier: 1.0 at deadline, 1.1 at open (linear)
    - Streak multiplier stacks on top of speed multiplier
    """

    EXACT_POINTS = 100
    NO_RESPONSE_PENALTY = -10
    SPEED_MAX_MULTIPLIER = 1.1
    RANK_POINTS = (50, 30, 20, 10)  # for ranks 2-5

    def score_submission(
        self,
        is_exact: bool,
        rank: int | None,
        submitted_at_ms: int,
        opened_at_ms: int,
        deadline_ms: int,
        current_streak: int,
    ) -> tuple[int, float]:
        """
        Calculate base points and speed multiplier for a submission.

        Args:
            is_exact: Whether prediction was exactly correct
            rank: Rank (1=exact, 2-N=closest, None=no response)
            submitted_at_ms: When prediction was submitted
            opened_at_ms: When window opened
            deadline_ms: Window deadline
            current_streak: Current streak (unused here, for context)

        Returns:
            Tuple of (base_points, speed_multiplier)
        """
        # No response penalty
        if rank is None:
            return (self.NO_RESPONSE_PENALTY, 1.0)

        # Calculate base points
        if is_exact or rank == 1:
            base_points = self.EXACT_POINTS
        elif 2 <= rank <= 5:
            base_points = self.RANK_POINTS[rank - 2]
        else:
            base_points = 0

        # Calculate speed multiplier (only for positive points)
        if base_points > 0:
            window_duration = deadline_ms - opened_at_ms
            time_taken = submitted_at_ms - opened_at_ms

            # Linear interpolation: 1.1 at start, 1.0 at deadline
            if time_taken <= 0:
                speed_multiplier = self.SPEED_MAX_MULTIPLIER
            elif time_taken >= window_duration:
                speed_multiplier = 1.0
            else:
                # Linear: 1.1 - (time_taken / window_duration) * 0.1
                ratio = time_taken / window_duration
                speed_multiplier = self.SPEED_MAX_MULTIPLIER - (ratio * 0.1)
        else:
            speed_multiplier = 1.0

        return (base_points, speed_multiplier)

    def apply_streak(
        self,
        base_points: int,
        speed_multiplier: float,
        streak_multiplier: float,
    ) -> int:
        """
        Apply speed and streak multipliers to base points.

        Args:
            base_points: Base points before multipliers
            speed_multiplier: Speed multiplier (1.0-1.1)
            streak_multiplier: Streak multiplier (1.0, 1.2, 1.5)

        Returns:
            Final points (rounded to integer)
        """
        # Never apply multipliers to negative points
        if base_points < 0:
            return base_points

        # Apply both multipliers
        final_points = base_points * speed_multiplier * streak_multiplier

        # Round to integer
        return round(final_points)
