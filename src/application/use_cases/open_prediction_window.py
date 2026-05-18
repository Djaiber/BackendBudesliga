"""Open prediction window use case."""

from typing import Any

from ...domain.entities import MatchEvent, PredictionWindow
from ...domain.ports import (
    AIGenerator,
    Clock,
    IdGenerator,
    WebSocketBroadcaster,
    WindowRepository,
)
from ...domain.services import GameEngineService

# Window duration in milliseconds (20 seconds)
WINDOW_DURATION_MS = 20_000


class OpenPredictionWindowUseCase:
    """
    Use case for opening a new prediction window.

    Selects game type, generates prompt, creates window, and broadcasts to room.
    """

    def __init__(
        self,
        window_repo: WindowRepository,
        broadcaster: WebSocketBroadcaster,
        ai_gen: AIGenerator,
        id_gen: IdGenerator,
        clock: Clock,
    ) -> None:
        """
        Initialize use case with dependencies.

        Args:
            window_repo: Window repository port
            broadcaster: WebSocket broadcaster port
            ai_gen: AI generator port
            id_gen: ID generator port
            clock: Clock port
        """
        self._window_repo = window_repo
        self._broadcaster = broadcaster
        self._ai_gen = ai_gen
        self._id_gen = id_gen
        self._clock = clock

    async def execute(
        self,
        room_id: str,
        recent_events: list[MatchEvent],
        correct_answer: str | int,
    ) -> PredictionWindow:
        """
        Execute open prediction window use case.

        Args:
            room_id: Room to open window for
            recent_events: Recent match events for game selection
            correct_answer: Correct answer for the prediction

        Returns:
            Created PredictionWindow
        """
        # Select game type based on recent events
        game_type = GameEngineService.select_game(recent_events)
        
        # Generate prompt
        context: dict[str, Any] = {
            "recent_events": [
                {
                    "event_type": e.event_type,
                    "minute": e.minute,
                    "second": e.second,
                    "team": e.team,
                }
                for e in recent_events
            ],
        }
        prompt = await self._ai_gen.generate_prompt(game_type, context)
        
        # Create window
        now_ms = self._clock.now_ms()
        window_id = self._id_gen.new_id("WIN")
        window = PredictionWindow(
            window_id=window_id,
            room_id=room_id,
            game_type=game_type,
            prompt=prompt,
            correct_answer=correct_answer,
            open_at_ms=now_ms,
            close_at_ms=now_ms + WINDOW_DURATION_MS,
            status="open",
        )
        await self._window_repo.save(window)
        
        # Broadcast to room
        await self._broadcaster.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "prediction_window_open",
                "window_id": window_id,
                "game_type": game_type,
                "prompt": prompt,
                "open_at_ms": now_ms,
                "close_at_ms": now_ms + WINDOW_DURATION_MS,
            },
        )
        
        return window
