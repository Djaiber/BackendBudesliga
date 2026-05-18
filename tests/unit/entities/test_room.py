"""Tests for Room entity."""

import pytest

from src.domain.entities import Player, Room


def test_room_happy_path() -> None:
    """Test creating a valid room."""
    players = (
        Player("user-1", "Alice", 100, Player.DUMMIES, 0),
        Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
        Player("user-3", "Charlie", 300, Player.AMATEUR, 2),
    )

    room = Room(
        room_id="room-123",
        players=players,
        status=Room.ACTIVE,
        created_at=1000000,
    )

    assert room.room_id == "room-123"
    assert len(room.players) == 3
    assert room.status == Room.ACTIVE


def test_room_too_many_players() -> None:
    """Test that more than MAX_PLAYERS raises ValueError."""
    players = tuple(
        Player(f"user-{i}", f"Player{i}", 0, Player.DUMMIES, 0) for i in range(5)
    )

    with pytest.raises(ValueError, match="players count must be 0-4"):
        Room(
            room_id="room-123",
            players=players,
            status=Room.ACTIVE,
            created_at=1000000,
        )


def test_room_invalid_status() -> None:
    """Test that invalid status raises ValueError."""
    with pytest.raises(ValueError, match="status must be one of"):
        Room(
            room_id="room-123",
            players=(),
            status="invalid_status",
            created_at=1000000,
        )


def test_room_is_mergeable_true() -> None:
    """Test is_mergeable returns True for active room with < 3 players."""
    players = (
        Player("user-1", "Alice", 100, Player.DUMMIES, 0),
        Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
    )

    room = Room(
        room_id="room-123",
        players=players,
        status=Room.ACTIVE,
        created_at=1000000,
    )

    assert room.is_mergeable() is True


def test_room_is_mergeable_false_enough_players() -> None:
    """Test is_mergeable returns False when room has >= 3 players."""
    players = (
        Player("user-1", "Alice", 100, Player.DUMMIES, 0),
        Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
        Player("user-3", "Charlie", 300, Player.AMATEUR, 2),
    )

    room = Room(
        room_id="room-123",
        players=players,
        status=Room.ACTIVE,
        created_at=1000000,
    )

    assert room.is_mergeable() is False


def test_room_is_mergeable_false_not_active() -> None:
    """Test is_mergeable returns False when room is not active."""
    players = (
        Player("user-1", "Alice", 100, Player.DUMMIES, 0),
        Player("user-2", "Bob", 200, Player.ENTHUSIAST, 1),
    )

    room = Room(
        room_id="room-123",
        players=players,
        status=Room.WAITING,
        created_at=1000000,
    )

    assert room.is_mergeable() is False


def test_room_is_frozen() -> None:
    """Test that Room is immutable."""
    room = Room(
        room_id="room-123",
        players=(),
        status=Room.WAITING,
        created_at=1000000,
    )

    with pytest.raises(Exception):  # FrozenInstanceError
        room.status = Room.ACTIVE  # type: ignore[misc]
