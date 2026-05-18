"""Fake ID generator for testing."""


class FakeIdGenerator:
    """Sequential ID generator for deterministic tests."""

    def __init__(self) -> None:
        """Initialize fake ID generator."""
        self._counters: dict[str, int] = {}

    def new_id(self, prefix: str) -> str:
        """
        Generate sequential ID with prefix.

        Args:
            prefix: Prefix for the ID (e.g., 'ROOM', 'WIN')

        Returns:
            ID like 'ROOM-1', 'ROOM-2', 'WIN-1', etc.
        """
        if prefix not in self._counters:
            self._counters[prefix] = 0
        self._counters[prefix] += 1
        return f"{prefix}-{self._counters[prefix]}"

    def reset(self) -> None:
        """Reset all counters."""
        self._counters.clear()
