"""Broadcast emoji use case."""

from ...domain.ports import RoomRepository, ScoreRepository, WebSocketBroadcaster
from ..dto import ALLOWED_EMOJIS


class BroadcastEmojiUseCase:
    """
    Use case for broadcasting emoji from a player to their room.

    Validates emoji is allowed and player is in room.
    """

    def __init__(
        self,
        room_repo: RoomRepository,
        score_repo: ScoreRepository,
        broadcaster: WebSocketBroadcaster,
    ) -> None:
        """
        Initialize use case with dependencies.

        Args:
            room_repo: Room repository port
            score_repo: Score repository port
            broadcaster: WebSocket broadcaster port
        """
        self._room_repo = room_repo
        self._score_repo = score_repo
        self._broadcaster = broadcaster

    async def execute(
        self,
        room_id: str,
        user_id: str,
        emoji: str,
    ) -> None:
        """
        Execute broadcast emoji use case.

        Args:
            room_id: Room to broadcast to
            user_id: Player sending emoji
            emoji: Emoji to broadcast

        Raises:
            ValueError: If emoji not allowed or player not in room
        """
        # Validate emoji
        if emoji not in ALLOWED_EMOJIS:
            raise ValueError(f"Emoji {emoji} not allowed")

        # Get room
        room = await self._room_repo.get(room_id)
        if room is None:
            raise ValueError(f"Room {room_id} not found")

        # Check player in room
        player_in_room = any(p.user_id == user_id for p in room.players)
        if not player_in_room:
            raise ValueError(f"Player {user_id} not in room {room_id}")

        # Get player name
        player = await self._score_repo.get_player(user_id)
        if player is None:
            raise ValueError(f"Player {user_id} not found")

        # Broadcast emoji
        await self._broadcaster.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "emoji_broadcast",
                "user_id": user_id,
                "player_name": player.name,
                "emoji": emoji,
            },
        )
