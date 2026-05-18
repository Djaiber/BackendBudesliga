"""Fake clock for testing."""


class FakeClock:
    """In-memory clock with controllable time."""

    def __init__(self, initial_ms: int = 0) -> None:
        """
        Initialize fake clock.

        Args:
            initial_ms: Starting time in epoch milliseconds
        """
        self._current_ms = initial_ms

    def now_ms(self) -> int:
        """Get current time in epoch milliseconds."""
        return self._current_ms

    def advance(self, delta_ms: int) -> None:
        """
        Advance clock by delta milliseconds.

        Args:
            delta_ms: Milliseconds to advance
        """
        self._current_ms += delta_ms

    def set(self, time_ms: int) -> None:
        """
        Set clock to specific time.

        Args:
            time_ms: Time in epoch milliseconds
        """
        self._current_ms = time_ms
