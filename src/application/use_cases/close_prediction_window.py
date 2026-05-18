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
        """
        Initialize use case with dependencies.

        Args:
            window_repo: Window repository port
            room_repo: Room repository port
            score_repo: Score repository port
            broadcaster: WebSocket broadcaster port
            clock: Clock port
        """
        self._window_repo = window_repo
        self._room_repo = room_repo
        self._score_repo = score_repo
        self._broadcaster = broadcaster
        self._clock = clock
        self._scoring_service = ScoringService()

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
        
        # Resolve predictions
        resolution = GameEngineService.resolve_predictions(
            predictions=predictions,
            correct_answer=window.correct_answer,
            game_type=window.game_type,
        )
        
        # Calculate scores for each player
        results: list[PredictionResultDTO] = []
        player_deltas: dict[str, int] = {}
        
        for player in room.players:
            # Get player's current state
            player_state = await self._score_repo.get_player(player.player_id)
            if player_state is None:
                # Should not happen, but handle gracefully
                player_state = Player(
                    player_id=player.player_id,
                    name=player.name,
                    score=0,
                    tier="Dummies",
                    streak=0,
                )
            
            # Find player's result
            player_result = next(
                (r for r in resolution if r.player_id == player.player_id),
                None,
            )
            
            if player_result is None:
                # Player didn't submit - penalty
                base_points, speed_mult = self._scoring_service.score_submission(
                    is_exact=False,
                    rank=None,
                    submitted_at_ms=0,
                    opened_at_ms=window.open_at_ms,
                    deadline_ms=window.close_at_ms,
                    current_streak=player_state.streak,
                )
                streak_mult = StreakService.get_multiplier(player_state.streak)
                points_earned = self._scoring_service.apply_streak(
                    base_points, speed_mult, streak_mult
                )
                
                # Update streak (no response = reset)
                new_streak = StreakService.update_streak(player_state.streak, False)
                
                results.append(
                    PredictionResultDTO(
                        player_id=player.player_id,
                        prediction=None,
                        points_earned=points_earned,
                        rank=None,
                        speed_multiplier=speed_mult,
                        streak_multiplier=streak_mult,
                    )
                )
            else:
                # Player submitted prediction
                base_points, speed_mult = self._scoring_service.score_submission(
                    is_exact=player_result.is_exact,
                    rank=player_result.rank,
                    submitted_at_ms=player_result.submitted_at_ms,
                    opened_at_ms=window.open_at_ms,
                    deadline_ms=window.close_at_ms,
                    current_streak=player_state.streak,
                )
                streak_mult = StreakService.get_multiplier(player_state.streak)
                points_earned = self._scoring_service.apply_streak(
                    base_points, speed_mult, streak_mult
                )
                
                # Update streak
                new_streak = StreakService.update_streak(
                    player_state.streak,
                    player_result.is_exact,
                )
                
                results.append(
                    PredictionResultDTO(
                        player_id=player.player_id,
                        prediction=player_result.value,
                        points_earned=points_earned,
                        rank=player_result.rank,
                        speed_multiplier=speed_mult,
                        streak_multiplier=streak_mult,
                    )
                )
            
            # Apply score delta
            new_score = player_state.score + points_earned
            new_tier = TierService.calculate_tier(new_score)
            
            delta = ScoreDelta(
                points_earned=points_earned,
                new_streak=new_streak,
                new_tier=new_tier,
            )
            await self._score_repo.apply_delta(player.player_id, delta)
            player_deltas[player.player_id] = points_earned
        
        # Broadcast results
        await self._broadcaster.broadcast_to_room(
            room_id=window.room_id,
            message={
                "type": "prediction_result",
                "window_id": window_id,
                "correct_answer": window.correct_answer,
                "results": results,
            },
        )
        
        # Broadcast updated leaderboard
        leaderboard = await self._score_repo.leaderboard(limit=10)
        await self._broadcaster.broadcast_to_room(
            room_id=window.room_id,
            message={
                "type": "leaderboard_update",
                "leaderboard": [
                    {
                        "player_id": p.player_id,
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
            correct_answer=window.correct_answer,
            player_deltas=player_deltas,
        )
