"""Fake event publisher for testing."""

from typing import Any


class FakeEventPublisher:
    """In-memory event publisher that captures published events."""

    def __init__(self) -> None:
        """Initialize fake publisher."""
        self.published: list[dict[str, Any]] = []

    async def publish(self, event_type: str, payload: dict[str, Any]) -> None:
        """Capture published event."""
        self.published.append({
            "event_type": event_type,
            "payload": payload,
        })

    def clear(self) -> None:
        """Clear published events."""
        self.published.clear()
