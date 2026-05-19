"""Close prediction window use case."""

from ...domain.entities import Player, ScoreDelta
from ...domain.ports import (
    Clock,
    RoomRepository,
    ScoreRepository,
    WebSocketBroadcaster,
    WindowRepository,
)
from ...domain.services import GameEngineService, ScoringService, StreakService, TierService
from ..dto import CloseWindowResult, PredictionResultDTO


class ClosePredictionWindowUseCase:
    """
    Use case for closing a prediction window and resolving results.

    Handles:
    - Resolving predictions and ranking players
    - Calculating points with speed and streak multipliers
    - Updating player scores and streaks
    - Broadcasting results to room
    """

    def __init__(
        self,
        window_repo: WindowRepository,
        room_repo: RoomRepository,
        score_repo: ScoreRepository,
        broadcaster: WebSocketBroadcaster,
        clock: Clock,
    ) -> None:
        self._window_repo = window_repo
        self._room_repo = room_repo
        self._score_repo = score_repo
        self._broadcaster = broadcaster
        self._clock = clock
        self._scoring_service = ScoringService()
        self._streak_service = StreakService()
        self._tier_service = TierService()
        self._game_engine = GameEngineService()

    async def execute(self, window_id: str) -> CloseWindowResult:
        """
        Execute close prediction window use case.

        Args:
            window_id: Window to close

        Returns:
            CloseWindowResult with points earned per player
        """
        # Get window
        window = await self._window_repo.get(window_id)
        if window is None:
            raise ValueError(f"Window {window_id} not found")

        # Close window
        now_ms = self._clock.now_ms()
        await self._window_repo.close(window_id, now_ms)

        # Broadcast window closed
        await self._broadcaster.broadcast_to_room(
            room_id=window.room_id,
            message={
                "type": "prediction_window_close",
                "window_id": window_id,
                "closed_at_ms": now_ms,
            },
        )

        # Get room and predictions
        room = await self._room_repo.get(window.room_id)
        if room is None:
            raise ValueError(f"Room {window.room_id} not found")

        predictions = await self._window_repo.list_predictions(window_id)

        # Rank predictions using game engine
        # resolve_window returns {user_id: rank}
        ranks = self._game_engine.resolve_window(
            window=window,
            predictions=predictions,
            events_after_close=[],  # No live events in use case context
        )

        # Determine correct answer from options or window game
        # For scoring purposes, rank 1 = exact/best
        correct_answer = window.options[0] if window.options else "N/A"

        # Calculate scores for each player
        results: list[PredictionResultDTO] = []
        player_deltas: dict[str, int] = {}

        for player in room.players:
            # Get player's current state
            player_state = await self._score_repo.get_player(player.user_id)
            if player_state is None:
                player_state = Player(
                    user_id=player.user_id,
                    name=player.name,
                    score=0,
                    tier="Dummies",
                    streak=0,
                )

            # Find player's prediction
            player_pred = next(
                (p for p in predictions if p.user_id == player.user_id),
                None,
            )
            player_rank = ranks.get(player.user_id)

            if player_pred is None or player_rank is None:
                # Player didn't submit or wasn't ranked - penalty
                base_points, speed_mult = self._scoring_service.score_submission(
                    is_exact=False,
                    rank=None,
                    submitted_at_ms=0,
                    opened_at_ms=window.opened_at_ms,
                    deadline_ms=window.deadline_ms,
                    current_streak=player_state.streak,
                )
                streak_mult = self._streak_service.multiplier_for(player_state.streak)
                points_earned = self._scoring_service.apply_streak(
                    base_points, speed_mult, streak_mult
                )
                new_streak = self._streak_service.next_streak(player_state.streak, False)

                results.append(
                    PredictionResultDTO(
                        user_id=player.user_id,
                        prediction=None,
                        points_earned=points_earned,
                        rank=None,
                        speed_multiplier=speed_mult,
                        streak_multiplier=streak_mult,
                    )
                )
            else:
                # Player submitted prediction
                is_exact = player_rank == 1
                base_points, speed_mult = self._scoring_service.score_submission(
                    is_exact=is_exact,
                    rank=player_rank,
                    submitted_at_ms=player_pred.submitted_at_ms,
                    opened_at_ms=window.opened_at_ms,
                    deadline_ms=window.deadline_ms,
                    current_streak=player_state.streak,
                )
                streak_mult = self._streak_service.multiplier_for(player_state.streak)
                points_earned = self._scoring_service.apply_streak(
                    base_points, speed_mult, streak_mult
                )
                new_streak = self._streak_service.next_streak(
                    player_state.streak, is_exact
                )

                results.append(
                    PredictionResultDTO(
                        user_id=player.user_id,
                        prediction=player_pred.value,
                        points_earned=points_earned,
                        rank=player_rank,
                        speed_multiplier=speed_mult,
                        streak_multiplier=streak_mult,
                    )
                )

            # Apply score delta
            new_score = max(0, player_state.score + points_earned)
            new_tier = self._tier_service.get_tier(new_score)

            delta = ScoreDelta(
                user_id=player.user_id,
                points=points_earned,
                new_score=new_score,
                new_streak=new_streak,
                new_tier=new_tier,
                multiplier_applied=speed_mult,
            )
            await self._score_repo.apply_delta(player.user_id, delta)
            player_deltas[player.user_id] = points_earned

        # Broadcast results
        await self._broadcaster.broadcast_to_room(
            room_id=window.room_id,
            message={
                "type": "prediction_result",
                "window_id": window_id,
                "correct_answer": correct_answer,
                "results": results,
            },
        )

        # Broadcast updated leaderboard
        leaderboard = await self._score_repo.leaderboard(window.room_id)
        await self._broadcaster.broadcast_to_room(
            room_id=window.room_id,
            message={
                "type": "leaderboard_update",
                "leaderboard": [
                    {
                        "user_id": p.user_id,
                        "name": p.name,
                        "score": p.score,
                        "tier": p.tier,
                        "streak": p.streak,
                        "rank": idx + 1,
                    }
                    for idx, p in enumerate(leaderboard)
                ],
            },
        )

        return CloseWindowResult(
            window_id=window_id,
            correct_answer=correct_answer,
            player_deltas=player_deltas,
        )
