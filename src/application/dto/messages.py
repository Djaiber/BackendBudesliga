"""WebSocket message DTOs matching frontend contract."""

from typing import Literal, TypedDict

from ...domain.entities import MatchEvent, Player

# Allowed emojis for broadcast
ALLOWED_EMOJIS = {"🔥", "👏", "😂", "😱", "🎯", "⚽"}


# ============================================================================
# INCOMING MESSAGES (from client)
# ============================================================================


class JoinRoomMessage(TypedDict):
    """Client request to join a room."""

    action: Literal["join_room"]
    room_id: str | None  # None = auto-match
    player_id: str
    player_name: str


class SubmitPredictionMessage(TypedDict):
    """Client submits a prediction for an open window."""

    action: Literal["submit_prediction"]
    window_id: str
    player_id: str
    value: str | int  # String for NEXT_GOAL_TIMING, int for others


class EmojiMessage(TypedDict):
    """Client broadcasts an emoji to the room."""

    action: Literal["emoji"]
    room_id: str
    player_id: str
    emoji: str


class PingMessage(TypedDict):
    """Client ping to keep connection alive."""

    action: Literal["ping"]


# ============================================================================
# OUTGOING MESSAGES (to client)
# ============================================================================


class PlayerDTO(TypedDict):
    """Player data transfer object."""

    player_id: str
    name: str
    score: int
    tier: str
    streak: int


class RoomJoinedMessage(TypedDict):
    """Sent to player who just joined a room."""

    type: Literal["room_joined"]
    room_id: str
    player: PlayerDTO
    players: list[PlayerDTO]  # All players in room including self


class RoomMergedMessage(TypedDict):
    """Broadcast when two rooms merge."""

    type: Literal["room_merged"]
    old_room_id: str
    new_room_id: str
    players: list[PlayerDTO]  # All players in merged room


class PlayerJoinedMessage(TypedDict):
    """Broadcast when a player joins the room."""

    type: Literal["player_joined"]
    player: PlayerDTO


class PlayerLeftMessage(TypedDict):
    """Broadcast when a player leaves the room."""

    type: Literal["player_left"]
    player_id: str


class PredictionWindowOpenMessage(TypedDict):
    """Broadcast when a new prediction window opens."""

    type: Literal["prediction_window_open"]
    window_id: str
    game_type: str
    prompt: str
    open_at_ms: int
    close_at_ms: int


class PredictionWindowCloseMessage(TypedDict):
    """Broadcast when a prediction window closes."""

    type: Literal["prediction_window_close"]
    window_id: str
    closed_at_ms: int


class PredictionResultMessage(TypedDict):
    """Broadcast prediction results after window closes."""

    type: Literal["prediction_result"]
    window_id: str
    correct_answer: str | int
    results: list["PredictionResultDTO"]


class PredictionResultDTO(TypedDict):
    """Individual player's prediction result."""

    player_id: str
    prediction: str | int | None
    points_earned: int
    rank: int | None  # None if no prediction
    speed_multiplier: float
    streak_multiplier: float


class MatchEventMessage(TypedDict):
    """Broadcast when a match event occurs."""

    type: Literal["match_event"]
    event_type: str
    minute: int
    second: int
    team: str
    player_name: str | None


class LeaderboardEntry(TypedDict):
    """Single leaderboard entry."""

    player_id: str
    name: str
    score: int
    tier: str
    streak: int
    rank: int


class LeaderboardUpdateMessage(TypedDict):
    """Broadcast updated leaderboard."""

    type: Literal["leaderboard_update"]
    leaderboard: list[LeaderboardEntry]


class EmojiBroadcastMessage(TypedDict):
    """Broadcast emoji from a player."""

    type: Literal["emoji_broadcast"]
    player_id: str
    player_name: str
    emoji: str


class PongMessage(TypedDict):
    """Response to ping."""

    type: Literal["pong"]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def player_to_dto(player: Player) -> PlayerDTO:
    """
    Convert domain Player entity to DTO.

    Args:
        player: Domain Player entity

    Returns:
        PlayerDTO for WebSocket messages
    """
    return PlayerDTO(
        player_id=player.player_id,
        name=player.name,
        score=player.score,
        tier=player.tier,
        streak=player.streak,
    )


def event_to_message(event: MatchEvent) -> MatchEventMessage:
    """
    Convert domain MatchEvent entity to WebSocket message.

    Args:
        event: Domain MatchEvent entity

    Returns:
        MatchEventMessage for broadcasting
    """
    return MatchEventMessage(
        type="match_event",
        event_type=event.event_type,
        minute=event.minute,
        second=event.second,
        team=event.team,
        player_name=event.player_name,
    )
