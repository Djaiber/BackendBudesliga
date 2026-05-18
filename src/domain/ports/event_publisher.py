"""Event publisher port - abstract interface for publishing domain events."""

from typing import Any, Protocol


class EventPublisher(Protocol):
    """
    Abstract publisher for domain events.

    All methods are async as real implementations will perform I/O.
    """

    async def publish(self, source: str, detail_type: str, detail: dict[str, Any]) -> None:
        """
        Publish a domain event.

        Args:
            source: Event source identifier (e.g., "connected-arena.game-engine")
            detail_type: Event type (e.g., "PredictionWindowOpened")
            detail: Event payload
        """
        ...
