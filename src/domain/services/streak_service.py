"""Streak service for tracking consecutive correct predictions."""


class StreakService:
    """
    Service for managing player prediction streaks.

    Streak multipliers:
    - 3+ correct: 1.2x
    - 5+ correct: 1.5x
    - Wrong answer resets streak to 0
    """

    def next_streak(self, current_streak: int, correct: bool) -> int:
        """
        Calculate next streak value based on prediction result.

        Args:
            current_streak: Current streak count
            correct: Whether the prediction was correct

        Returns:
            New streak count (incremented if correct, reset to 0 if wrong)
        """
        if correct:
            return current_streak + 1
        else:
            return 0

    def multiplier_for(self, streak: int) -> float:
        """
        Get score multiplier for a given streak.

        Args:
            streak: Current streak count

        Returns:
            Multiplier (1.0, 1.2, or 1.5)
        """
        if streak >= 5:
            return 1.5
        elif streak >= 3:
            return 1.2
        else:
            return 1.0
