"""Tests for MatchmakerService."""

from src.domain.entities import Player, Room
from src.domain.services.matchmaker_service import MatchmakerService


def test_matchmaker_two_rooms_with_2_players_each() -> None:
    """Test that two rooms with 2 players each are paired."""
    service = MatchmakerService()

    room1 = Room(
        room_id="room-1",
        players=(
            Player("user-1", "Alice", 100, Player.DUMMIES, 0),
            Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
        ),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    room2 = Room(
        room_id="room-2",
        players=(
            Player("user-3", "Charlie", 300, Player.AMATEUR, 2),
            Player("user-4", "Dave", 400, Player.SAVVY, 3),
        ),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    pairs = service.find_merge_candidates([room1, room2])

    assert len(pairs) == 1
    assert pairs[0] == (room1, room2)


def test_matchmaker_two_rooms_exceed_max() -> None:
    """Test that rooms with combined size > MAX_PLAYERS are not paired."""
    service = MatchmakerService()

    room1 = Room(
        room_id="room-1",
        players=(
            Player("user-1", "Alice", 100, Player.DUMMIES, 0),
            Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
        ),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    room2 = Room(
        room_id="room-2",
        players=(
            Player("user-3", "Charlie", 300, Player.AMATEUR, 2),
            Player("user-4", "Dave", 400, Player.SAVVY, 3),
            Player("user-5", "Eve", 500, Player.SAVVY, 4),
        ),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    pairs = service.find_merge_candidates([room1, room2])

    assert len(pairs) == 0


def test_matchmaker_one_small_room_no_partner() -> None:
    """Test that a single small room returns empty list."""
    service = MatchmakerService()

    room1 = Room(
        room_id="room-1",
        players=(
            Player("user-1", "Alice", 100, Player.DUMMIES, 0),
            Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
        ),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    pairs = service.find_merge_candidates([room1])

    assert len(pairs) == 0


def test_matchmaker_no_duplicate_pairing() -> None:
    """Test that rooms are not paired twice."""
    service = MatchmakerService()

    room1 = Room(
        room_id="room-1",
        players=(Player("user-1", "Alice", 100, Player.DUMMIES, 0),),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    room2 = Room(
        room_id="room-2",
        players=(Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    room3 = Room(
        room_id="room-3",
        players=(Player("user-3", "Charlie", 300, Player.AMATEUR, 2),),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    pairs = service.find_merge_candidates([room1, room2, room3])

    # Should pair room1 with room2, leaving room3 unpaired
    assert len(pairs) == 1
    assert room1.room_id in (pairs[0][0].room_id, pairs[0][1].room_id)
    assert room2.room_id in (pairs[0][0].room_id, pairs[0][1].room_id)


def test_matchmaker_can_join_active_not_full() -> None:
    """Test can_join returns True for active room with space."""
    service = MatchmakerService()

    room = Room(
        room_id="room-1",
        players=(
            Player("user-1", "Alice", 100, Player.DUMMIES, 0),
            Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
            Player("user-3", "Charlie", 300, Player.AMATEUR, 2),
        ),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    assert service.can_join(room) is True


def test_matchmaker_can_join_full_room() -> None:
    """Test can_join returns False for full room."""
    service = MatchmakerService()

    room = Room(
        room_id="room-1",
        players=(
            Player("user-1", "Alice", 100, Player.DUMMIES, 0),
            Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
            Player("user-3", "Charlie", 300, Player.AMATEUR, 2),
            Player("user-4", "Dave", 400, Player.SAVVY, 3),
        ),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    assert service.can_join(room) is False


def test_matchmaker_can_join_waiting_room() -> None:
    """Test can_join returns False for waiting room."""
    service = MatchmakerService()

    room = Room(
        room_id="room-1",
        players=(
            Player("user-1", "Alice", 100, Player.DUMMIES, 0),
            Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
        ),
        status=Room.WAITING,
        created_at=1000000,
    )

    assert service.can_join(room) is False


def test_matchmaker_ignores_non_active_rooms() -> None:
    """Test that non-active rooms are not considered for merging."""
    service = MatchmakerService()

    room1 = Room(
        room_id="room-1",
        players=(Player("user-1", "Alice", 100, Player.DUMMIES, 0),),
        status=Room.WAITING,  # Not active
        created_at=1000000,
    )

    room2 = Room(
        room_id="room-2",
        players=(Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    pairs = service.find_merge_candidates([room1, room2])

    assert len(pairs) == 0


def test_matchmaker_ignores_rooms_with_enough_players() -> None:
    """Test that rooms with >= MIN_PLAYERS are not merged."""
    service = MatchmakerService()

    room1 = Room(
        room_id="room-1",
        players=(
            Player("user-1", "Alice", 100, Player.DUMMIES, 0),
            Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
            Player("user-3", "Charlie", 300, Player.AMATEUR, 2),
        ),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    room2 = Room(
        room_id="room-2",
        players=(Player("user-4", "Dave", 400, Player.SAVVY, 3),),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    pairs = service.find_merge_candidates([room1, room2])

    assert len(pairs) == 0  # room1 has enough players, room2 has no partner


def test_matchmaker_can_join_empty_room() -> None:
    """Test can_join returns True for empty active room."""
    service = MatchmakerService()

    room = Room(
        room_id="room-1",
        players=(),
        status=Room.ACTIVE,
        created_at=1000000,
    )

    assert service.can_join(room) is True
