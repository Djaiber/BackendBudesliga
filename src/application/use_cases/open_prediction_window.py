"""Open prediction window use case."""

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
        self._window_repo = window_repo
        self._broadcaster = broadcaster
        self._ai_gen = ai_gen
        self._id_gen = id_gen
        self._clock = clock
        self._game_engine = GameEngineService()

    async def execute(
        self,
        room_id: str,
        recent_events: list[MatchEvent],
        correct_answer: str | int,
        team_a: str = "",
        team_b: str = "",
    ) -> PredictionWindow:
        """
        Execute open prediction window use case.

        Args:
            room_id: Room to open window for
            recent_events: Recent match events for game selection
            correct_answer: Correct answer for the prediction
            team_a: First team identifier for AI prompt generation
            team_b: Second team identifier for AI prompt generation

        Returns:
            Created PredictionWindow
        """
        now_ms = self._clock.now_ms()

        # Select game type based on recent events (instance method)
        game = self._game_engine.select_game(recent_events, now_ms)

        # Generate prompt text and optional answer options from AI
        prompt_text, options = await self._ai_gen.generate_prompt(
            game, recent_events, team_a, team_b
        )

        # Create window
        window_id = self._id_gen.new_id("WIN")
        window = PredictionWindow(
            window_id=window_id,
            room_id=room_id,
            game=game,
            prompt=prompt_text,
            opened_at_ms=now_ms,
            deadline_ms=now_ms + WINDOW_DURATION_MS,
            options=options,
            status="open",
        )
        await self._window_repo.save(window)

        # Broadcast to room
        await self._broadcaster.broadcast_to_room(
            room_id=room_id,
            message={
                "type": "prediction_window_open",
                "window_id": window_id,
                "game": game,
                "prompt": prompt_text,
                "opened_at_ms": now_ms,
                "deadline_ms": now_ms + WINDOW_DURATION_MS,
            },
        )

        return window
