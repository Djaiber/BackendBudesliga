"""Window repository port - abstract interface for prediction window persistence."""

from typing import Protocol

from ..entities import Prediction, PredictionWindow


class WindowRepository(Protocol):
    """
    Abstract repository for prediction window persistence.

    Manages prediction windows and their associated predictions.
    """

    async def get(self, window_id: str) -> PredictionWindow | None:
        """
        Get a prediction window by ID.

        Args:
            window_id: Unique window identifier

        Returns:
            PredictionWindow if found, None otherwise
        """
        ...

    async def save(self, window: PredictionWindow) -> None:
        """
        Save or update a prediction window.

        Args:
            window: PredictionWindow to persist
        """
        ...

    async def list_open_by_room(self, room_id: str) -> list[PredictionWindow]:
        """
        List all open prediction windows for a room.

        Args:
            room_id: Room identifier

        Returns:
            List of open PredictionWindows (may be empty)
        """
        ...

    async def add_prediction(self, window_id: str, prediction: Prediction) -> None:
        """
        Add a prediction to a window.

        Args:
            window_id: Window identifier
            prediction: Prediction to add
        """
        ...

    async def list_predictions(self, window_id: str) -> list[Prediction]:
        """
        List all predictions for a window.

        Args:
            window_id: Window identifier

        Returns:
            List of Predictions (may be empty)
        """
        ...

    async def close(self, window_id: str, now_ms: int) -> None:
        """
        Close a prediction window.

        Args:
            window_id: Window identifier
            now_ms: Current time in epoch milliseconds
        """
        ...
