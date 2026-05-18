"""Fake score repository for testing."""

from src.domain.entities import Player, ScoreDelta


class FakeScoreRepository:
    """In-memory score repository for testing."""

    def __init__(self) -> None:
        """Initialize fake repository."""
        self.players: dict[str, Player] = {}

    async def get_player(self, player_id: str) -> Player | None:
        """Get player by ID."""
        return self.players.get(player_id)

    async def upsert_player(self, player: Player) -> None:
        """Insert or update player."""
        self.players[player.player_id] = player

    async def apply_delta(self, player_id: str, delta: ScoreDelta) -> Player:
        """Apply score delta to player."""
        player = self.players.get(player_id)
        if player is None:
            raise ValueError(f"Player {player_id} not found")
        
        # Create updated player
        new_score = player.score + delta.points_earned
        updated_player = Player(
            player_id=player.player_id,
            name=player.name,
            score=new_score,
            tier=delta.new_tier,
            streak=delta.new_streak,
        )
        self.players[player_id] = updated_player
        return updated_player

    async def leaderboard(self, limit: int = 10) -> list[Player]:
        """Get top players by score."""
        sorted_players = sorted(
            self.players.values(),
            key=lambda p: p.score,
            reverse=True,
        )
        return sorted_players[:limit]

    def clear(self) -> None:
        """Clear all players."""
        self.players.clear()
