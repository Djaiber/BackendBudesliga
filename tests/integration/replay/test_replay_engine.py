"""Integration tests for ReplayEngine."""

from __future__ import annotations

import asyncio
import time

import pytest

from src.domain.entities import MatchEvent
from src.infrastructure.clock.system_clock import SystemClock
from src.infrastructure.replay.replay_engine import ReplayEngine
from tests.unit.application.fakes.fake_clock import FakeClock
from tests.unit.application.fakes.fake_event_publisher import FakeEventPublisher

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(
    event_id: str, minute: int, second: int = 0, event_type: str = "GOAL"
) -> MatchEvent:
    return MatchEvent(
        event_id=event_id,
        minute=minute,
        second=second,
        event_type=event_type,
        team="home",
        player=None,
        x_position=None,
        y_position=None,
        metadata={},
    )


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------


def test_empty_events_raises_value_error() -> None:
    """Empty events list → ValueError at construction."""
    publisher = FakeEventPublisher()
    clock = FakeClock()
    with pytest.raises(ValueError, match="empty"):
        ReplayEngine(events=[], publisher=publisher, clock=clock)


def test_speed_factor_zero_raises_value_error() -> None:
    """speed_factor=0 → ValueError at construction."""
    publisher = FakeEventPublisher()
    clock = FakeClock()
    events = [make_event("e1", 0)]
    with pytest.raises(ValueError, match="speed_factor"):
        ReplayEngine(events=events, publisher=publisher, clock=clock, speed_factor=0)


def test_speed_factor_negative_raises_value_error() -> None:
    """speed_factor=-1 → ValueError at construction."""
    publisher = FakeEventPublisher()
    clock = FakeClock()
    events = [make_event("e1", 0)]
    with pytest.raises(ValueError, match="speed_factor"):
        ReplayEngine(events=events, publisher=publisher, clock=clock, speed_factor=-1)


def test_unsorted_events_raise_value_error() -> None:
    """Events not sorted by (minute, second) → ValueError at construction."""
    publisher = FakeEventPublisher()
    clock = FakeClock()
    events = [
        make_event("e1", 2, 0),
        make_event("e2", 0, 30),
    ]
    with pytest.raises(ValueError, match="sorted"):
        ReplayEngine(events=events, publisher=publisher, clock=clock, speed_factor=600)


# ---------------------------------------------------------------------------
# Functional behaviour — fast playback (speed_factor=600 → ~200ms wall time)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publishes_all_events_in_order() -> None:
    """3 events published in order with correct payload shape."""
    publisher = FakeEventPublisher()
    events = [
        make_event("e1", 0, 0, "GOAL"),
        make_event("e2", 1, 0, "PASS"),
        make_event("e3", 2, 0, "SHOT"),
    ]
    engine = ReplayEngine(
        events=events,
        publisher=publisher,
        clock=SystemClock(),
        speed_factor=600,
    )
    await engine.run()

    assert len(publisher.published) == 3
    assert publisher.published[0]["detail"]["event_id"] == "e1"
    assert publisher.published[1]["detail"]["event_id"] == "e2"
    assert publisher.published[2]["detail"]["event_id"] == "e3"


@pytest.mark.asyncio
async def test_event_payload_shape() -> None:
    """Published payload matches HandleMatchEventUseCase-expected fields."""
    publisher = FakeEventPublisher()
    event = MatchEvent(
        event_id="evt-42",
        minute=15,
        second=30,
        event_type="GOAL",
        team="away",
        player="Müller",
        x_position=50.0,
        y_position=34.0,
        metadata={},
    )
    engine = ReplayEngine(
        events=[event],
        publisher=publisher,
        clock=SystemClock(),
        speed_factor=600,
    )
    await engine.run()

    assert len(publisher.published) == 1
    published = publisher.published[0]
    detail = published["detail"]

    assert detail["event_id"] == "evt-42"
    assert detail["minute"] == 15
    assert detail["second"] == 30
    assert detail["event_type"] == "GOAL"
    assert detail["team"] == "away"
    assert detail["player"] == "Müller"


@pytest.mark.asyncio
async def test_source_and_detail_type_passed_correctly() -> None:
    """source and detail_type are forwarded to publisher.publish()."""
    publisher = FakeEventPublisher()
    events = [make_event("e1", 0)]
    engine = ReplayEngine(
        events=events,
        publisher=publisher,
        clock=SystemClock(),
        speed_factor=600,
        source="test.replay",
        detail_type="TestEvent",
    )
    await engine.run()

    assert publisher.published[0]["source"] == "test.replay"
    assert publisher.published[0]["detail_type"] == "TestEvent"


@pytest.mark.asyncio
async def test_speed_factor_600_completes_quickly() -> None:
    """speed_factor=600 with events at 0:0, 1:0, 2:0 completes in < 1 second."""
    publisher = FakeEventPublisher()
    events = [
        make_event("e1", 0, 0),
        make_event("e2", 1, 0),
        make_event("e3", 2, 0),
    ]
    engine = ReplayEngine(
        events=events,
        publisher=publisher,
        clock=SystemClock(),
        speed_factor=600,
    )

    start = time.monotonic()
    await engine.run()
    elapsed = time.monotonic() - start

    assert len(publisher.published) == 3
    assert elapsed < 1.0, f"Expected < 1s with speed_factor=600, got {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_speed_factor_60_takes_approximately_two_seconds() -> None:
    """speed_factor=60 with events at 0:0, 1:0, 2:0 takes ~2 seconds real time."""
    publisher = FakeEventPublisher()
    events = [
        make_event("e1", 0, 0),
        make_event("e2", 1, 0),
        make_event("e3", 2, 0),
    ]
    engine = ReplayEngine(
        events=events,
        publisher=publisher,
        clock=SystemClock(),
        speed_factor=60,
    )

    start = time.monotonic()
    await engine.run()
    elapsed = time.monotonic() - start

    assert len(publisher.published) == 3
    assert 1.5 < elapsed < 3.0, f"Expected ~2s with speed_factor=60, got {elapsed:.2f}s"


# ---------------------------------------------------------------------------
# stop() behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_interrupts_run() -> None:
    """stop() called mid-run exits cleanly without publishing remaining events."""
    publisher = FakeEventPublisher()
    # 5 events, 1 minute apart — speed_factor=30 means 2s per minute
    events = [make_event(f"e{i}", i, 0) for i in range(5)]
    engine = ReplayEngine(
        events=events,
        publisher=publisher,
        clock=SystemClock(),
        speed_factor=30,
    )

    async def stopper() -> None:
        # Wait enough for the first event to be published then stop
        await asyncio.sleep(0.2)
        await engine.stop()

    await asyncio.gather(engine.run(), stopper())

    # At least the first event published; but not all 5
    assert 1 <= len(publisher.published) < 5
