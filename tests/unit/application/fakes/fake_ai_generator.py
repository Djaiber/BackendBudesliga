"""Fake AI generator for testing."""

from src.domain.entities import MatchEvent


class FakeAIGenerator:
    """Stub AI generator that returns predefined prompts."""

    def __init__(
        self,
        default_prompt: str = "Test prompt",
        default_options: tuple[str, ...] | None = None,
    ) -> None:
        self.default_prompt = default_prompt
        self.default_options = default_options
        self.calls: list[dict[str, object]] = []

    async def generate_prompt(
        self,
        game: str,
        recent_events: list[MatchEvent],
        team_a: str,
        team_b: str,
    ) -> tuple[str, tuple[str, ...] | None]:
        self.calls.append(
            {
                "game": game,
                "recent_events": recent_events,
                "team_a": team_a,
                "team_b": team_b,
            }
        )
        return self.default_prompt, self.default_options

    def clear(self) -> None:
        self.calls.clear()
