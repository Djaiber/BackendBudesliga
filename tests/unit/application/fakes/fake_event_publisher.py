"""Fake event publisher for testing."""

from typing import Any


class FakeEventPublisher:
    """In-memory event publisher that captures published events."""

    def __init__(self) -> None:
        self.published: list[dict[str, Any]] = []

    async def publish(self, source: str, detail_type: str, detail: dict[str, Any]) -> None:
        self.published.append(
            {
                "source": source,
                "detail_type": detail_type,
                "detail": detail,
            }
        )

    def clear(self) -> None:
        self.published.clear()
