"""System clock implementation using time.time()."""

import time


class SystemClock:
    """
    Real-world clock implementation using system time.

    Implements the Clock port using Python's time.time().
    """

    def now_ms(self) -> int:
        """
        Get current time in epoch milliseconds.

        Returns:
            Current time as milliseconds since epoch
        """
        return int(time.time() * 1000)
