"""Clock port - abstract interface for time operations."""

from typing import Protocol


class Clock(Protocol):
    """
    Abstract clock for getting current time.

    Allows use cases to get current time without directly calling time.time(),
    making them deterministic and testable.
    """

    def now_ms(self) -> int:
        """
        Get current time in epoch milliseconds.

        Returns:
            Current time as milliseconds since epoch
        """
        ...
