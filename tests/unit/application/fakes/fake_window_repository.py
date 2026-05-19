"""Fake window repository for testing."""

from src.domain.entities import Prediction, PredictionWindow


class FakeWindowRepository:
    """In-memory window repository for testing."""

    def __init__(self) -> None:
        """Initialize fake repository."""
        self.windows: dict[str, PredictionWindow] = {}
        self.predictions: dict[str, list[Prediction]] = {}

    async def get(self, window_id: str) -> PredictionWindow | None:
        """Get window by ID."""
        return self.windows.get(window_id)

    async def save(self, window: PredictionWindow) -> None:
        """Save or update window."""
        self.windows[window.window_id] = window

    async def list_open_by_room(self, room_id: str) -> list[PredictionWindow]:
        """List open windows for room."""
        return [w for w in self.windows.values() if w.room_id == room_id and w.status == "open"]

    async def add_prediction(self, window_id: str, prediction: Prediction) -> None:
        """Add prediction to window."""
        if window_id not in self.predictions:
            self.predictions[window_id] = []
        self.predictions[window_id].append(prediction)

    async def list_predictions(self, window_id: str) -> list[Prediction]:
        """List predictions for window."""
        return self.predictions.get(window_id, [])

    async def close(self, window_id: str, now_ms: int) -> None:
        """Close window."""
        window = self.windows.get(window_id)
        if window is None:
            raise ValueError(f"Window {window_id} not found")

        # Create closed window
        self.windows[window_id] = PredictionWindow(
            window_id=window.window_id,
            room_id=window.room_id,
            game=window.game,
            prompt=window.prompt,
            opened_at_ms=window.opened_at_ms,
            deadline_ms=window.deadline_ms,
            options=window.options,
            status="closed",
        )

    def clear(self) -> None:
        """Clear all windows and predictions."""
        self.windows.clear()
        self.predictions.clear()
