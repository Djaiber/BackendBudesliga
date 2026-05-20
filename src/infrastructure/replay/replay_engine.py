"""Replay engine — publishes a sorted list of MatchEvents at configurable speed."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.domain.entities import MatchEvent
from src.domain.ports import Clock, EventPublisher

logger = logging.getLogger(__name__)


class ReplayEngine:
    """Replays a sorted list of MatchEvent at configurable speed.

    speed_factor = 60 means 1 match minute compresses to 1 real second.
    speed_factor = 1 means real-time playback.
    """

    def __init__(
        self,
        events: list[MatchEvent],
        publisher: EventPublisher,
        clock: Clock,
        speed_factor: int = 60,
        source: str = "replay",
        detail_type: str = "MatchEvent",
    ) -> None:
        if speed_factor < 1:
            raise ValueError("speed_factor must be >= 1")
        if not events:
            raise ValueError("events must not be empty")

        _assert_sorted(events)

        self._events = events
        self._publisher = publisher
        self._clock = clock
        self._speed_factor = speed_factor
        self._source = source
        self._detail_type = detail_type
        self._stopped = False

    async def run(self) -> None:
        """Publish each event at its scheduled real-world time.

        Sequential — does NOT publish in parallel.  Order matters.
        """
        self._stopped = False
        start_ms = self._clock.now_ms()

        for event in self._events:
            if self._stopped:
                break

            event_match_time_ms = (event.minute * 60 + event.second) * 1000
            event_real_time_ms = event_match_time_ms / self._speed_factor
            wait_ms = event_real_time_ms - (self._clock.now_ms() - start_ms)

            if wait_ms > 0:
                await asyncio.sleep(wait_ms / 1000)

            # Re-read _stopped after await — another coroutine may have called stop()
            stopped: bool = self._stopped
            if stopped:
                break

            payload: dict[str, Any] = {
                "event_id": event.event_id,
                "minute": event.minute,
                "second": event.second,
                "event_type": event.event_type,
                "team": event.team,
                "player": event.player,
                "metadata": event.metadata,
            }
            await self._publisher.publish(self._source, self._detail_type, payload)
            logger.debug("Published event %s at %d:%02d", event.event_id, event.minute, event.second)

    async def stop(self) -> None:
        """Signal the running loop to stop after the current event publishes."""
        self._stopped = True


def _assert_sorted(events: list[MatchEvent]) -> None:
    """Raise ValueError if events are not sorted by (minute, second)."""
    for i in range(1, len(events)):
        prev = events[i - 1]
        curr = events[i]
        if (curr.minute, curr.second) < (prev.minute, prev.second):
            raise ValueError(
                f"events must be sorted by (minute, second); "
                f"event[{i - 1}] is at {prev.minute}:{prev.second:02d} "
                f"but event[{i}] is at {curr.minute}:{curr.second:02d}"
            )
