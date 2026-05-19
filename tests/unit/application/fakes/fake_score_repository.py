"""Fake score repository for testing."""

from src.domain.entities import Player, ScoreDelta


class FakeScoreRepository:
    """In-memory score repository for testing."""

    def __init__(self) -> None:
        """Initialize fake repository."""
        self.players: dict[str, Player] = {}

    async def get_player(self, user_id: str) -> Player | None:
        """Get player by ID."""
        return self.players.get(user_id)

    async def upsert_player(self, player: Player) -> None:
        """Insert or update player."""
        self.players[player.user_id] = player

    async def apply_delta(self, delta: ScoreDelta) -> Player:
        """Apply score delta to player."""
        player = self.players.get(delta.user_id)
        if player is None:
            raise ValueError(f"Player {delta.user_id} not found")

        updated_player = Player(
            user_id=player.user_id,
            name=player.name,
            score=delta.new_score,
            tier=delta.new_tier,
            streak=delta.new_streak,
        )
        self.players[delta.user_id] = updated_player
        return updated_player

    async def leaderboard(self, room_id: str) -> list[Player]:
        """Get players sorted by score descending."""
        return sorted(
            self.players.values(),
            key=lambda p: p.score,
            reverse=True,
        )

    def clear(self) -> None:
        """Clear all players."""
        self.players.clear()
