"""Tests for broadcast emoji use case."""

import pytest

from src.application.use_cases import BroadcastEmojiUseCase
from src.domain.entities import Player, Room
from tests.unit.application.fakes import (
    FakeRoomRepository,
    FakeScoreRepository,
    FakeWebSocketBroadcaster,
)


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
) -> BroadcastEmojiUseCase:
    """Create broadcast emoji use case."""
    return BroadcastEmojiUseCase(
        room_repo=room_repo,
        score_repo=score_repo,
        broadcaster=broadcaster,
    )


@pytest.mark.asyncio
async def test_broadcast_allowed_emoji(
    use_case: BroadcastEmojiUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
) -> None:
    """Test broadcasting allowed emoji succeeds."""
    # Setup player
    player = Player(
        user_id="p1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=0,
    )
    await score_repo.upsert_player(player)
    
    # Setup room
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at=1000000,
    )
    await room_repo.save(room)
    
    # Broadcast emoji
    await use_case.execute(
        room_id="ROOM-1",
        user_id="p1",
        emoji="🔥",
    )
    
    # Check broadcast
    assert len(broadcaster.broadcast_to_room_calls) == 1
    msg = broadcaster.broadcast_to_room_calls[0]
    assert msg["room_id"] == "ROOM-1"
    assert msg["message"]["type"] == "emoji_broadcast"
    assert msg["message"]["user_id"] == "p1"
    assert msg["message"]["player_name"] == "Alice"
    assert msg["message"]["emoji"] == "🔥"


@pytest.mark.asyncio
async def test_broadcast_all_allowed_emojis(
    use_case: BroadcastEmojiUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
) -> None:
    """Test all allowed emojis can be broadcast."""
    # Setup
    player = Player(
        user_id="p1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=0,
    )
    await score_repo.upsert_player(player)
    
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at=1000000,
    )
    await room_repo.save(room)
    
    # Test each allowed emoji
    allowed = ["🔥", "👏", "😂", "😱", "🎯", "⚽"]
    for emoji in allowed:
        await use_case.execute(
            room_id="ROOM-1",
            user_id="p1",
            emoji=emoji,
        )
    
    # All succeeded
    assert len(broadcaster.broadcast_to_room_calls) == 6


@pytest.mark.asyncio
async def test_broadcast_disallowed_emoji_raises_error(
    use_case: BroadcastEmojiUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
) -> None:
    """Test broadcasting disallowed emoji raises error."""
    # Setup
    player = Player(
        user_id="p1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=0,
    )
    await score_repo.upsert_player(player)
    
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at=1000000,
    )
    await room_repo.save(room)
    
    # Try disallowed emoji
    with pytest.raises(ValueError, match="not allowed"):
        await use_case.execute(
            room_id="ROOM-1",
            user_id="p1",
            emoji="💩",
        )


@pytest.mark.asyncio
async def test_broadcast_from_nonexistent_room_raises_error(
    use_case: BroadcastEmojiUseCase,
) -> None:
    """Test broadcasting from nonexistent room raises error."""
    with pytest.raises(ValueError, match="Room ROOM-999 not found"):
        await use_case.execute(
            room_id="ROOM-999",
            user_id="p1",
            emoji="🔥",
        )


@pytest.mark.asyncio
async def test_broadcast_from_player_not_in_room_raises_error(
    use_case: BroadcastEmojiUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
) -> None:
    """Test broadcasting from player not in room raises error."""
    # Setup player
    player = Player(
        user_id="p1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=0,
    )
    await score_repo.upsert_player(player)
    
    # Setup room without player
    other_player = Player(
        user_id="p2",
        name="Bob",
        score=0,
        tier="Dummies",
        streak=0,
    )
    room = Room(
        room_id="ROOM-1",
        players=(other_player,),
        status="active",
        created_at=1000000,
    )
    await room_repo.save(room)
    
    # Try to broadcast
    with pytest.raises(ValueError, match="not in room"):
        await use_case.execute(
            room_id="ROOM-1",
            user_id="p1",
            emoji="🔥",
        )


@pytest.mark.asyncio
async def test_broadcast_from_nonexistent_player_raises_error(
    use_case: BroadcastEmojiUseCase,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
) -> None:
    """Test broadcasting from nonexistent player raises error."""
    # Setup player in room
    player = Player(
        user_id="p1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=0,
    )
    await score_repo.upsert_player(player)
    
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at=1000000,
    )
    await room_repo.save(room)
    
    # Delete player from score repo
    score_repo.players.clear()
    
    # Try to broadcast
    with pytest.raises(ValueError, match="Player p1 not found"):
        await use_case.execute(
            room_id="ROOM-1",
            user_id="p1",
            emoji="🔥",
        )
