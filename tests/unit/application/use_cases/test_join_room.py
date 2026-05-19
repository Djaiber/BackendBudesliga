"""Tests for join room use case."""

import pytest

from src.application.use_cases import JoinRoomUseCase
from src.domain.entities import Player, Room
from tests.unit.application.fakes import (
    FakeClock,
    FakeIdGenerator,
    FakeRoomRepository,
    FakeScoreRepository,
    FakeWebSocketBroadcaster,
)


@pytest.fixture
def clock() -> FakeClock:
    """Create fake clock."""
    return FakeClock(initial_ms=1000000)


@pytest.fixture
def id_gen() -> FakeIdGenerator:
    """Create fake ID generator."""
    return FakeIdGenerator()


@pytest.fixture
def room_repo() -> FakeRoomRepository:
    """Create fake room repository."""
    return FakeRoomRepository()


@pytest.fixture
def score_repo() -> FakeScoreRepository:
    """Create fake score repository."""
    return FakeScoreRepository()


@pytest.fixture
def broadcaster() -> FakeWebSocketBroadcaster:
    """Create fake broadcaster."""
    return FakeWebSocketBroadcaster()


@pytest.fixture
def use_case(
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
    id_gen: FakeIdGenerator,
    clock: FakeClock,
) -> JoinRoomUseCase:
    """Create join room use case."""
    return JoinRoomUseCase(
        room_repo=room_repo,
        score_repo=score_repo,
        broadcaster=broadcaster,
        id_gen=id_gen,
        clock=clock,
    )


@pytest.mark.asyncio
async def test_new_player_creates_new_room(
    use_case: JoinRoomUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
) -> None:
    """Test new player creates new room when no mergeable rooms exist."""
    result = await use_case.execute(
        user_id="p1",
        player_name="Alice",
        connection_id="conn1",
        room_id=None,
    )
    
    # Check result
    assert result.room.room_id == "ROOM-1"
    assert len(result.room.players) == 1
    assert result.player.user_id == "p1"
    assert result.player.name == "Alice"
    assert result.player.score == 0
    assert result.player.tier == "Dummies"
    assert result.was_merged is False
    
    # Check player saved
    saved_player = await score_repo.get_player("p1")
    assert saved_player is not None
    assert saved_player.name == "Alice"
    
    # Check room saved
    saved_room = await room_repo.get("ROOM-1")
    assert saved_room is not None
    assert len(saved_room.players) == 1
    
    # Check broadcast
    assert len(broadcaster.sent_to_connection) == 1
    msg = broadcaster.sent_to_connection[0]
    assert msg["connection_id"] == "conn1"
    assert msg["message"]["type"] == "room_joined"
    assert msg["message"]["room_id"] == "ROOM-1"


@pytest.mark.asyncio
async def test_existing_player_joins_new_room(
    use_case: JoinRoomUseCase,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
) -> None:
    """Test existing player with score joins new room."""
    # Create existing player
    existing = Player(
        user_id="p1",
        name="Alice",
        score=500,
        tier="Enthusiast",
        streak=3,
    )
    await score_repo.upsert_player(existing)
    
    result = await use_case.execute(
        user_id="p1",
        player_name="Alice",
        connection_id="conn1",
        room_id=None,
    )
    
    # Check player stats preserved
    assert result.player.score == 500
    assert result.player.tier == "Enthusiast"
    assert result.player.streak == 3
    
    # Check broadcast includes correct stats
    msg = broadcaster.sent_to_connection[0]["message"]
    assert msg["player"]["score"] == 500
    assert msg["player"]["tier"] == "Enthusiast"


@pytest.mark.asyncio
async def test_player_joins_mergeable_room(
    use_case: JoinRoomUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
    clock: FakeClock,
) -> None:
    """Test player auto-joins existing mergeable room."""
    # Create existing player in room
    p1 = Player(user_id="p1", name="Alice", score=0, tier="Dummies", streak=0)
    await score_repo.upsert_player(p1)
    
    room = Room(
        room_id="ROOM-1",
        players=(p1,),
        status="active",
        created_at=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # New player joins
    result = await use_case.execute(
        user_id="p2",
        player_name="Bob",
        connection_id="conn2",
        room_id=None,
    )
    
    # Check joined existing room
    assert result.room.room_id == "ROOM-1"
    assert len(result.room.players) == 2
    assert result.was_merged is False
    
    # Check broadcasts
    assert len(broadcaster.broadcast_to_room_calls) == 1
    assert len(broadcaster.sent_to_connection) == 1
    
    # Check player_joined broadcast
    broadcast = broadcaster.broadcast_to_room_calls[0]
    assert broadcast["room_id"] == "ROOM-1"
    assert broadcast["message"]["type"] == "player_joined"
    assert broadcast["message"]["player"]["user_id"] == "p2"
    assert broadcast["exclude_connection_id"] == "conn2"


@pytest.mark.asyncio
async def test_player_joins_specific_room(
    use_case: JoinRoomUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
    clock: FakeClock,
) -> None:
    """Test player joins specific room by ID."""
    # Create room
    p1 = Player(user_id="p1", name="Alice", score=0, tier="Dummies", streak=0)
    await score_repo.upsert_player(p1)
    
    room = Room(
        room_id="ROOM-123",
        players=(p1,),
        status="active",
        created_at=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # Join specific room
    result = await use_case.execute(
        user_id="p2",
        player_name="Bob",
        connection_id="conn2",
        room_id="ROOM-123",
    )
    
    assert result.room.room_id == "ROOM-123"
    assert len(result.room.players) == 2


@pytest.mark.asyncio
async def test_join_nonexistent_room_raises_error(
    use_case: JoinRoomUseCase,
) -> None:
    """Test joining nonexistent room raises error."""
    with pytest.raises(ValueError, match="Room ROOM-999 not found"):
        await use_case.execute(
            user_id="p1",
            player_name="Alice",
            connection_id="conn1",
            room_id="ROOM-999",
        )


@pytest.mark.asyncio
async def test_join_full_room_raises_error(
    use_case: JoinRoomUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    clock: FakeClock,
) -> None:
    """Test joining full room raises error."""
    # Create full room (4 players)
    players = []
    for i in range(4):
        p = Player(
            user_id=f"p{i}",
            name=f"Player{i}",
            score=0,
            tier="Dummies",
            streak=0,
        )
        await score_repo.upsert_player(p)
        players.append(p)
    
    room = Room(
        room_id="ROOM-FULL",
        players=tuple(players),
        status="active",
        created_at=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # Try to join
    with pytest.raises(ValueError, match="Room ROOM-FULL is full"):
        await use_case.execute(
            user_id="p5",
            player_name="Eve",
            connection_id="conn5",
            room_id="ROOM-FULL",
        )


@pytest.mark.asyncio
async def test_skips_non_mergeable_rooms(
    use_case: JoinRoomUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    clock: FakeClock,
) -> None:
    """Test auto-match skips rooms with 3+ players."""
    # Create room with 3 players (not mergeable)
    players = []
    for i in range(3):
        p = Player(
            user_id=f"p{i}",
            name=f"Player{i}",
            score=0,
            tier="Dummies",
            streak=0,
        )
        await score_repo.upsert_player(p)
        players.append(p)
    
    room = Room(
        room_id="ROOM-BUSY",
        players=tuple(players),
        status="active",
        created_at=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # New player should create new room
    result = await use_case.execute(
        user_id="p4",
        player_name="Dave",
        connection_id="conn4",
        room_id=None,
    )
    
    assert result.room.room_id == "ROOM-1"  # New room
    assert len(result.room.players) == 1
