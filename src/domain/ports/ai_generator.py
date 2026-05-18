"""AI generator port - abstract interface for AI prompt generation."""

from typing import Protocol

from src.domain.entities import MatchEvent


class AIGenerator(Protocol):
    """
    Abstract generator for AI-powered prompts.

    All methods are async as real implementations will perform I/O.
    """

    async def generate_prompt(
        self,
        game: str,
        recent_events: list[MatchEvent],
        team_a: str,
        team_b: str,
    ) -> tuple[str, tuple[str, ...] | None]:
        """
        Generate a contextual prompt for a mini-game.

        Args:
            game: Game type (NEXT_GOAL_TIMING, etc.)
            recent_events: Recent match events for context
            team_a: First team identifier
            team_b: Second team identifier

        Returns:
            Tuple of (prompt text, optional answer options)
        """
        ...
