"""WebSocket message DTOs matching frontend contract."""

from typing import Literal, TypedDict

from ...domain.entities import MatchEvent, Player

# Allowed emojis for broadcast
ALLOWED_EMOJIS = {"🔥", "👏", "😂", "😱", "🎯", "⚽"}


class MatchInfo(TypedDict):
    """Parsed match metadata from MatchInformations_Anonym.xml."""

    match_id: str
    team_a: str
    team_b: str
    kickoff_iso: str
    lineups: dict[str, list[str]]


# ============================================================================
# INCOMING MESSAGES (from client)
# ============================================================================


class JoinRoomMessage(TypedDict):
    """Client request to join a room."""

    action: Literal["join_room"]
    room_id: str | None  # None = auto-match
    user_id: str
    player_name: str


class SubmitPredictionMessage(TypedDict):
    """Client submits a prediction for an open window."""

    action: Literal["submit_prediction"]
    window_id: str
    user_id: str
    value: str | int  # String for NEXT_GOAL_TIMING, int for others


class EmojiMessage(TypedDict):
    """Client broadcasts an emoji to the room."""

    action: Literal["emoji"]
    room_id: str
    user_id: str
    emoji: str


class PingMessage(TypedDict):
    """Client ping to keep connection alive."""

    action: Literal["ping"]


# ============================================================================
# OUTGOING MESSAGES (to client)
# ============================================================================


class PlayerDTO(TypedDict):
    """Player data transfer object."""

    user_id: str
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
    user_id: str


class PredictionWindowOpenMessage(TypedDict, total=False):
    """Broadcast when a new prediction window opens."""

    type: Literal["prediction_window_open"]
    window_id: str
    game: str
    prompt: str
    deadline_ms: int
    opened_at_ms: int
    options: list[str]


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

    user_id: str
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

    user_id: str
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
    user_id: str
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
        user_id=player.user_id,
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
    # Map team IDs to 'home' or 'away' for frontend
    # DFL-CLU-000001 = Bayern (home), DFL-CLU-000002 = Hamburg (away)
    team_side = event.team
    if event.team == "DFL-CLU-000001":
        team_side = "home"
    elif event.team == "DFL-CLU-000002":
        team_side = "away"

    return MatchEventMessage(
        type="match_event",
        event_type=event.event_type,
        minute=event.minute,
        second=event.second,
        team=team_side,
        player_name=event.player,
    )
