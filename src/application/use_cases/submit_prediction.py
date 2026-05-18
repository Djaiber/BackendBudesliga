"""Submit prediction use case."""

from ...domain.entities import Prediction
from ...domain.ports import Clock, WindowRepository
from ..dto import SubmitPredictionResult


class SubmitPredictionUseCase:
    """
    Use case for submitting a prediction to an open window.

    Validates window is open and stores prediction.
    """

    def __init__(
        self,
        window_repo: WindowRepository,
        clock: Clock,
    ) -> None:
        """
        Initialize use case with dependencies.

        Args:
            window_repo: Window repository port
            clock: Clock port
        """
        self._window_repo = window_repo
        self._clock = clock

    async def execute(
        self,
        window_id: str,
        player_id: str,
        value: str | int,
    ) -> SubmitPredictionResult:
        """
        Execute submit prediction use case.

        Args:
            window_id: Prediction window ID
            player_id: Player submitting prediction
            value: Prediction value (string or int depending on game type)

        Returns:
            SubmitPredictionResult with success status
        """
        # Get window
        window = await self._window_repo.get(window_id)
        if window is None:
            return SubmitPredictionResult(
                success=False,
                error=f"Window {window_id} not found",
            )
        
        # Check window is open
        if window.status != "open":
            return SubmitPredictionResult(
                success=False,
                error=f"Window {window_id} is not open",
            )
        
        # Check window not expired
        now_ms = self._clock.now_ms()
        if window.is_expired(now_ms):
            return SubmitPredictionResult(
                success=False,
                error=f"Window {window_id} has expired",
            )
        
        # Check for duplicate prediction
        existing_predictions = await self._window_repo.list_predictions(window_id)
        if any(p.player_id == player_id for p in existing_predictions):
            return SubmitPredictionResult(
                success=False,
                error=f"Player {player_id} already submitted prediction",
            )
        
        # Create and store prediction
        prediction = Prediction(
            player_id=player_id,
            value=value,
            submitted_at_ms=now_ms,
        )
        await self._window_repo.add_prediction(window_id, prediction)
        
        return SubmitPredictionResult(success=True)
