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
    """Create fake room repository."""
    return FakeRoomRepository()


@pytest.fixture
def broadcaster() -> FakeWebSocketBroadcaster:
    """Create fake broadcaster."""
    return FakeWebSocketBroadcaster()


@pytest.fixture
def event_publisher() -> FakeEventPublisher:
    """Create fake event publisher."""
    return FakeEventPublisher()


@pytest.fixture
def use_case(
    room_repo: FakeRoomRepository,
    broadcaster: FakeWebSocketBroadcaster,
    event_publisher: FakeEventPublisher,
) -> HandleMatchEventUseCase:
    """Create handle match event use case."""
    return HandleMatchEventUseCase(
        room_repo=room_repo,
        broadcaster=broadcaster,
        event_publisher=event_publisher,
    )


@pytest.mark.asyncio
async def test_handle_event_broadcasts_to_all_active_rooms(
    use_case: HandleMatchEventUseCase,
    room_repo: FakeRoomRepository,
    broadcaster: FakeWebSocketBroadcaster,
) -> None:
    """Test event is broadcast to all active rooms."""
    # Create active rooms
    p1 = Player(player_id="p1", name="Alice", score=0, tier="Dummies", streak=0)
    p2 = Player(player_id="p2", name="Bob", score=0, tier="Dummies", streak=0)
    
    room1 = Room(
        room_id="ROOM-1",
        players=(p1,),
        status="active",
        created_at_ms=1000000,
    )
    room2 = Room(
        room_id="ROOM-2",
        players=(p2,),
        status="active",
        created_at_ms=1000000,
    )
    await room_repo.save(room1)
    await room_repo.save(room2)
    
    # Handle event
    event = MatchEvent(
        event_type="goal",
        minute=15,
        second=30,
        team="home",
        player_name="Alice",
    )
    await use_case.execute(event)
    
    # Check broadcasts
    assert len(broadcaster.broadcast_to_room) == 2
    
    # Check both rooms received message
    room_ids = {b["room_id"] for b in broadcaster.broadcast_to_room}
    assert room_ids == {"ROOM-1", "ROOM-2"}
    
    # Check message format
    msg = broadcaster.broadcast_to_room[0]["message"]
    assert msg["type"] == "match_event"
    assert msg["event_type"] == "goal"
    assert msg["minute"] == 15
    assert msg["second"] == 30
    assert msg["team"] == "home"
    assert msg["player_name"] == "Alice"


@pytest.mark.asyncio
async def test_handle_event_skips_inactive_rooms(
    use_case: HandleMatchEventUseCase,
    room_repo: FakeRoomRepository,
    broadcaster: FakeWebSocketBroadcaster,
) -> None:
    """Test event is not broadcast to inactive rooms."""
    # Create rooms with different statuses
    p1 = Player(player_id="p1", name="Alice", score=0, tier="Dummies", streak=0)
    p2 = Player(player_id="p2", name="Bob", score=0, tier="Dummies", streak=0)
    
    active_room = Room(
        room_id="ROOM-ACTIVE",
        players=(p1,),
        status="active",
        created_at_ms=1000000,
    )
    inactive_room = Room(
        room_id="ROOM-INACTIVE",
        players=(p2,),
        status="inactive",
        created_at_ms=1000000,
    )
    await room_repo.save(active_room)
    await room_repo.save(inactive_room)
    
    # Handle event
    event = MatchEvent(
        event_type="corner",
        minute=10,
        second=0,
        team="away",
    )
    await use_case.execute(event)
    
    # Only active room receives broadcast
    assert len(broadcaster.broadcast_to_room) == 1
    assert broadcaster.broadcast_to_room[0]["room_id"] == "ROOM-ACTIVE"


@pytest.mark.asyncio
async def test_handle_event_publishes_to_event_bus(
    use_case: HandleMatchEventUseCase,
    event_publisher: FakeEventPublisher,
) -> None:
    """Test event is published to event bus."""
    event = MatchEvent(
        event_type="shot",
        minute=20,
        second=15,
        team="home",
        player_name="Bob",
    )
    await use_case.execute(event)
    
    # Check event published
    assert len(event_publisher.published) == 1
    published = event_publisher.published[0]
    assert published["event_type"] == "match_event"
    assert published["payload"]["event_type"] == "shot"
    assert published["payload"]["minute"] == 20
    assert published["payload"]["player_name"] == "Bob"


@pytest.mark.asyncio
async def test_handle_event_with_no_active_rooms(
    use_case: HandleMatchEventUseCase,
    broadcaster: FakeWebSocketBroadcaster,
    event_publisher: FakeEventPublisher,
) -> None:
    """Test handling event when no active rooms exist."""
    event = MatchEvent(
        event_type="goal",
        minute=5,
        second=0,
        team="away",
    )
    await use_case.execute(event)
    
    # No broadcasts
    assert len(broadcaster.broadcast_to_room) == 0
    
    # Still published to event bus
    assert len(event_publisher.published) == 1
