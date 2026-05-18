"""Tests for merge inactive rooms use case."""

import pytest

from src.application.use_cases import MergeInactiveRoomsUseCase
from src.domain.entities import Player, Room
from tests.unit.application.fakes import (
    FakeClock,
    FakeRoomRepository,
    FakeWebSocketBroadcaster,
)


@pytest.fixture
def clock() -> FakeClock:
    """Create fake clock."""
    return FakeClock(initial_ms=1000000)


@pytest.fixture
def room_repo() -> FakeRoomRepository:
    """Create fake room repository."""
    return FakeRoomRepository()


@pytest.fixture
def broadcaster() -> FakeWebSocketBroadcaster:
    """Create fake broadcaster."""
    return FakeWebSocketBroadcaster()


@pytest.fixture
def use_case(
    room_repo: FakeRoomRepository,
    broadcaster: FakeWebSocketBroadcaster,
    clock: FakeClock,
) -> MergeInactiveRoomsUseCase:
    """Create merge inactive rooms use case."""
    return MergeInactiveRoomsUseCase(
        room_repo=room_repo,
        broadcaster=broadcaster,
        clock=clock,
    )


@pytest.mark.asyncio
async def test_merge_two_small_rooms(
    use_case: MergeInactiveRoomsUseCase,
    room_repo: FakeRoomRepository,
    broadcaster: FakeWebSocketBroadcaster,
    clock: FakeClock,
) -> None:
    """Test merging two rooms with <3 players each."""
    # Create two small rooms
    p1 = Player(player_id="p1", name="Alice", score=0, tier="Dummies", streak=0)
    p2 = Player(player_id="p2", name="Bob", score=0, tier="Dummies", streak=0)
    
    room1 = Room(
        room_id="ROOM-1",
        players=(p1,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    room2 = Room(
        room_id="ROOM-2",
        players=(p2,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room1)
    await room_repo.save(room2)
    
    # Merge
    merged_count = await use_case.execute()
    
    # Check merge happened
    assert merged_count == 1
    
    # Check room1 has both players
    merged_room = await room_repo.get("ROOM-1")
    assert merged_room is not None
    assert len(merged_room.players) == 2
    assert {p.player_id for p in merged_room.players} == {"p1", "p2"}
    
    # Check room2 deleted
    deleted_room = await room_repo.get("ROOM-2")
    assert deleted_room is None
    
    # Check broadcasts (2 messages: one to each room)
    assert len(broadcaster.broadcast_to_room) == 2
    
    # Check message format
    msg = broadcaster.broadcast_to_room[0]["message"]
    assert msg["type"] == "room_merged"
    assert msg["old_room_id"] == "ROOM-2"
    assert msg["new_room_id"] == "ROOM-1"
    assert len(msg["players"]) == 2


@pytest.mark.asyncio
async def test_merge_multiple_pairs(
    use_case: MergeInactiveRoomsUseCase,
    room_repo: FakeRoomRepository,
    clock: FakeClock,
) -> None:
    """Test merging multiple pairs of rooms."""
    # Create 4 small rooms
    players = [
        Player(player_id=f"p{i}", name=f"Player{i}", score=0, tier="Dummies", streak=0)
        for i in range(4)
    ]
    
    for i, player in enumerate(players):
        room = Room(
            room_id=f"ROOM-{i+1}",
            players=(player,),
            status="active",
            created_at_ms=clock.now_ms(),
        )
        await room_repo.save(room)
    
    # Merge
    merged_count = await use_case.execute()
    
    # Check 2 merges happened
    assert merged_count == 2
    
    # Check ROOM-1 and ROOM-3 exist with 2 players each
    room1 = await room_repo.get("ROOM-1")
    room3 = await room_repo.get("ROOM-3")
    assert room1 is not None
    assert room3 is not None
    assert len(room1.players) == 2
    assert len(room3.players) == 2
    
    # Check ROOM-2 and ROOM-4 deleted
    assert await room_repo.get("ROOM-2") is None
    assert await room_repo.get("ROOM-4") is None


@pytest.mark.asyncio
async def test_no_merge_when_combined_exceeds_limit(
    use_case: MergeInactiveRoomsUseCase,
    room_repo: FakeRoomRepository,
    clock: FakeClock,
) -> None:
    """Test rooms not merged if combined players exceed 4."""
    # Create two rooms with 2 players each (total would be 4, which is OK)
    # But create one with 3 players (not mergeable)
    p1 = Player(player_id="p1", name="P1", score=0, tier="Dummies", streak=0)
    p2 = Player(player_id="p2", name="P2", score=0, tier="Dummies", streak=0)
    p3 = Player(player_id="p3", name="P3", score=0, tier="Dummies", streak=0)
    p4 = Player(player_id="p4", name="P4", score=0, tier="Dummies", streak=0)
    
    room1 = Room(
        room_id="ROOM-1",
        players=(p1, p2, p3),  # 3 players - not mergeable
        status="active",
        created_at_ms=clock.now_ms(),
    )
    room2 = Room(
        room_id="ROOM-2",
        players=(p4,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room1)
    await room_repo.save(room2)
    
    # Try merge
    merged_count = await use_case.execute()
    
    # No merge (room1 has 3 players, not mergeable)
    assert merged_count == 0
    
    # Both rooms still exist
    assert await room_repo.get("ROOM-1") is not None
    assert await room_repo.get("ROOM-2") is not None


@pytest.mark.asyncio
async def test_no_merge_when_no_mergeable_rooms(
    use_case: MergeInactiveRoomsUseCase,
    room_repo: FakeRoomRepository,
    clock: FakeClock,
) -> None:
    """Test no merge when all rooms have 3+ players."""
    # Create rooms with 3+ players
    players1 = [
        Player(player_id=f"p{i}", name=f"P{i}", score=0, tier="Dummies", streak=0)
        for i in range(3)
    ]
    players2 = [
        Player(player_id=f"p{i+3}", name=f"P{i+3}", score=0, tier="Dummies", streak=0)
        for i in range(4)
    ]
    
    room1 = Room(
        room_id="ROOM-1",
        players=tuple(players1),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    room2 = Room(
        room_id="ROOM-2",
        players=tuple(players2),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room1)
    await room_repo.save(room2)
    
    # Try merge
    merged_count = await use_case.execute()
    
    # No merge
    assert merged_count == 0


@pytest.mark.asyncio
async def test_no_merge_when_only_one_room(
    use_case: MergeInactiveRoomsUseCase,
    room_repo: FakeRoomRepository,
    clock: FakeClock,
) -> None:
    """Test no merge when only one room exists."""
    p1 = Player(player_id="p1", name="Alice", score=0, tier="Dummies", streak=0)
    
    room = Room(
        room_id="ROOM-1",
        players=(p1,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # Try merge
    merged_count = await use_case.execute()
    
    # No merge
    assert merged_count == 0
    
    # Room still exists
    assert await room_repo.get("ROOM-1") is not None


@pytest.mark.asyncio
async def test_merge_preserves_room1_metadata(
    use_case: MergeInactiveRoomsUseCase,
    room_repo: FakeRoomRepository,
    clock: FakeClock,
) -> None:
    """Test merge preserves first room's ID and created_at."""
    p1 = Player(player_id="p1", name="Alice", score=0, tier="Dummies", streak=0)
    p2 = Player(player_id="p2", name="Bob", score=0, tier="Dummies", streak=0)
    
    room1 = Room(
        room_id="ROOM-FIRST",
        players=(p1,),
        status="active",
        created_at_ms=1000000,
    )
    room2 = Room(
        room_id="ROOM-SECOND",
        players=(p2,),
        status="active",
        created_at_ms=2000000,
    )
    await room_repo.save(room1)
    await room_repo.save(room2)
    
    await use_case.execute()
    
    # Check merged room has room1's metadata
    merged = await room_repo.get("ROOM-FIRST")
    assert merged is not None
    assert merged.room_id == "ROOM-FIRST"
    assert merged.created_at_ms == 1000000
    assert merged.status == "active"
