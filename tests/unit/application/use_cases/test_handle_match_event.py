"""Tests for handle match event use case."""

import pytest

from src.application.use_cases import HandleMatchEventUseCase
from src.domain.entities import MatchEvent, Player, Room
from tests.unit.application.fakes import (
    FakeEventPublisher,
    FakeRoomRepository,
    FakeWebSocketBroadcaster,
)


@pytest.fixture
def room_repo() -> FakeRoomRepository:
    return FakeRoomRepository()


@pytest.fixture
def broadcaster() -> FakeWebSocketBroadcaster:
    return FakeWebSocketBroadcaster()


@pytest.fixture
def event_publisher() -> FakeEventPublisher:
    return FakeEventPublisher()


@pytest.fixture
def use_case(
    room_repo: FakeRoomRepository,
    broadcaster: FakeWebSocketBroadcaster,
    event_publisher: FakeEventPublisher,
) -> HandleMatchEventUseCase:
    return HandleMatchEventUseCase(
        room_repo=room_repo,
        broadcaster=broadcaster,
        event_publisher=event_publisher,
    )


def make_event(
    event_type: str, minute: int, second: int = 0, team: str = "home", player: str | None = None
) -> MatchEvent:
    """Helper to build a MatchEvent with required fields."""
    return MatchEvent(
        event_id=f"{event_type}-{minute}-{second}",
        minute=minute,
        second=second,
        event_type=event_type,
        team=team,
        player=player,
        x_position=None,
        y_position=None,
        metadata={},
    )


@pytest.mark.asyncio
async def test_handle_event_broadcasts_to_all_active_rooms(
    use_case: HandleMatchEventUseCase,
    room_repo: FakeRoomRepository,
    broadcaster: FakeWebSocketBroadcaster,
) -> None:
    """Test event is broadcast to all active rooms."""
    p1 = Player(user_id="p1", name="Alice", score=0, tier="Dummies", streak=0)
    p2 = Player(user_id="p2", name="Bob", score=0, tier="Dummies", streak=0)

    room1 = Room(room_id="ROOM-1", players=(p1,), status="active", created_at=1000000)
    room2 = Room(room_id="ROOM-2", players=(p2,), status="active", created_at=1000000)
    await room_repo.save(room1)
    await room_repo.save(room2)

    event = make_event("GOAL", 15, 30, "home", "Alice")
    await use_case.execute(event)

    assert len(broadcaster.broadcast_to_room_calls) == 2
    room_ids = {b["room_id"] for b in broadcaster.broadcast_to_room_calls}
    assert room_ids == {"ROOM-1", "ROOM-2"}

    msg = broadcaster.broadcast_to_room_calls[0]["message"]
    assert msg["type"] == "match_event"
    assert msg["event_type"] == "GOAL"
    assert msg["minute"] == 15
    assert msg["second"] == 30
    assert msg["team"] == "home"


@pytest.mark.asyncio
async def test_handle_event_skips_inactive_rooms(
    use_case: HandleMatchEventUseCase,
    room_repo: FakeRoomRepository,
    broadcaster: FakeWebSocketBroadcaster,
) -> None:
    """Test event is not broadcast to inactive rooms."""
    p1 = Player(user_id="p1", name="Alice", score=0, tier="Dummies", streak=0)
    p2 = Player(user_id="p2", name="Bob", score=0, tier="Dummies", streak=0)

    active_room = Room(room_id="ROOM-ACTIVE", players=(p1,), status="active", created_at=1000000)
    # "waiting" is a valid status but not "active" so list_by_status("active") won't return it
    waiting_room = Room(room_id="ROOM-WAITING", players=(p2,), status="waiting", created_at=1000000)
    await room_repo.save(active_room)
    await room_repo.save(waiting_room)

    event = make_event("CORNER_KICK", 10, 0, "away")
    await use_case.execute(event)

    assert len(broadcaster.broadcast_to_room_calls) == 1
    assert broadcaster.broadcast_to_room_calls[0]["room_id"] == "ROOM-ACTIVE"


@pytest.mark.asyncio
async def test_handle_event_publishes_to_event_bus(
    use_case: HandleMatchEventUseCase,
    event_publisher: FakeEventPublisher,
) -> None:
    """Test event is published to event bus."""
    event = make_event("SHOT", 20, 15, "home", "Bob")
    await use_case.execute(event)

    assert len(event_publisher.published) == 1
    published = event_publisher.published[0]
    assert published["source"] == "connected-arena.game-engine"
    assert published["detail_type"] == "MatchEvent"
    assert published["detail"]["event_type"] == "SHOT"
    assert published["detail"]["minute"] == 20
    assert published["detail"]["player"] == "Bob"


@pytest.mark.asyncio
async def test_handle_event_with_no_active_rooms(
    use_case: HandleMatchEventUseCase,
    broadcaster: FakeWebSocketBroadcaster,
    event_publisher: FakeEventPublisher,
) -> None:
    """Test handling event when no active rooms exist."""
    event = make_event("GOAL", 5, 0, "away")
    await use_case.execute(event)

    assert len(broadcaster.broadcast_to_room_calls) == 0
    assert len(event_publisher.published) == 1
