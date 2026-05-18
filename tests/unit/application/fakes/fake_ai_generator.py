"""Fake AI generator for testing."""

from typing import Any


class FakeAIGenerator:
    """Stub AI generator that returns predefined prompts."""

    def __init__(self, default_prompt: str = "Test prompt") -> None:
        """
        Initialize fake AI generator.

        Args:
            default_prompt: Default prompt to return
        """
        self.default_prompt = default_prompt
        self.calls: list[dict[str, Any]] = []

    async def generate_prompt(
        self,
        game_type: str,
        context: dict[str, Any],
    ) -> str:
        """
        Return stub prompt and capture call.

        Args:
            game_type: Type of mini-game
            context: Context for prompt generation

        Returns:
            Stub prompt
        """
        self.calls.append({
            "game_type": game_type,
            "context": context,
        })
        return self.default_prompt

    def clear(self) -> None:
        """Clear captured calls."""
        self.calls.clear()
