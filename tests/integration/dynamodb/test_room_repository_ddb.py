"""Tests for DynamoDB Room Repository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.entities import Player, Room
from src.infrastructure.dynamodb.room_repository_ddb import RoomRepositoryDDB


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table."""
    table = AsyncMock()
    table.query = AsyncMock()
    table.put_item = AsyncMock()
    table.delete_item = AsyncMock()

    # Mock batch_writer as a context manager
    batch_writer_mock = AsyncMock()
    batch_writer_mock.__aenter__ = AsyncMock(return_value=batch_writer_mock)
    batch_writer_mock.__aexit__ = AsyncMock(return_value=None)
    batch_writer_mock.put_item = AsyncMock()
    batch_writer_mock.delete_item = AsyncMock()
    table.batch_writer = MagicMock(return_value=batch_writer_mock)

    return table


@pytest.fixture
def repository(mock_table):
    """Create repository instance with mocked table."""
    repo = RoomRepositoryDDB(
        table_name="test-table",
        region="eu-central-1",
    )

    # Create a mock resource that acts as an async context manager
    mock_ddb = AsyncMock()
    mock_ddb.Table = AsyncMock(return_value=mock_table)
    mock_ddb.__aenter__ = AsyncMock(return_value=mock_ddb)
    mock_ddb.__aexit__ = AsyncMock(return_value=None)

    # Patch the session.resource to return the mock directly (not a coroutine)
    def mock_resource(*args, **kwargs):
        return mock_ddb

    repo._session.resource = mock_resource
    return repo


@pytest.mark.asyncio
async def test_get_returns_none_when_room_not_found(repository: RoomRepositoryDDB, mock_table):
    """Test get returns None for nonexistent room."""
    # Mock empty query response
    mock_table.query.return_value = {"Items": []}

    room = await repository.get("nonexistent")
    assert room is None

    # Verify query was called with correct PK
    mock_table.query.assert_called_once()
    call_kwargs = mock_table.query.call_args[1]
    assert call_kwargs["ExpressionAttributeValues"][":pk"] == "ROOM#nonexistent"


@pytest.mark.asyncio
async def test_save_and_get_round_trip(repository: RoomRepositoryDDB, mock_table):
    """Test save + get preserves all room fields."""
    # Create room with players
    players = (
        Player(user_id="user1", name="Alice", score=100, tier="Dummies", streak=2),
        Player(user_id="user2", name="Bob", score=200, tier="Enthusiast", streak=3),
    )
    room = Room(
        room_id="room123",
        players=players,
        status="active",
        created_at=1000000,
    )

    # Mock query for existing players (empty)
    mock_table.query.return_value = {"Items": []}

    # Save
    await repository.save(room)

    # Verify batch_writer was used
    assert mock_table.batch_writer.called

    # Now mock get to return the saved room
    mock_table.query.return_value = {
        "Items": [
            {
                "PK": "ROOM#room123",
                "SK": "METADATA",
                "status": "active",
                "created_at": 1000000,
                "GSI1_PK": "STATUS#active",
                "GSI1_SK": 1000000,
            },
            {
                "PK": "ROOM#room123",
                "SK": "PLAYER#user1",
                "user_id": "user1",
                "name": "Alice",
                "score": 100,
                "tier": "Dummies",
                "streak": 2,
            },
            {
                "PK": "ROOM#room123",
                "SK": "PLAYER#user2",
                "user_id": "user2",
                "name": "Bob",
                "score": 200,
                "tier": "Enthusiast",
                "streak": 3,
            },
        ]
    }

    # Get
    retrieved = await repository.get("room123")

    # Verify
    assert retrieved is not None
    assert retrieved.room_id == "room123"
    assert retrieved.status == "active"
    assert retrieved.created_at == 1000000
    assert len(retrieved.players) == 2

    # Check players
    player_ids = {p.user_id for p in retrieved.players}
    assert player_ids == {"user1", "user2"}

    alice = next(p for p in retrieved.players if p.user_id == "user1")
    assert alice.name == "Alice"
    assert alice.score == 100
    assert alice.tier == "Dummies"
    assert alice.streak == 2


@pytest.mark.asyncio
async def test_save_overwrites_existing_room(repository: RoomRepositoryDDB, mock_table):
    """Test save replaces existing room completely."""
    # Mock query for existing players (one player)
    mock_table.query.side_effect = [
        # First call: query for existing players
        {
            "Items": [
                {
                    "PK": "ROOM#room123",
                    "SK": "PLAYER#user1",
                    "user_id": "user1",
                    "name": "Alice",
                    "score": 100,
                    "tier": "Dummies",
                    "streak": 0,
                }
            ]
        },
        # Second call: query for get after save
        {
            "Items": [
                {
                    "PK": "ROOM#room123",
                    "SK": "METADATA",
                    "status": "waiting",
                    "created_at": 1000000,
                    "GSI1_PK": "STATUS#waiting",
                    "GSI1_SK": 1000000,
                },
                {
                    "PK": "ROOM#room123",
                    "SK": "PLAYER#user2",
                    "user_id": "user2",
                    "name": "Bob",
                    "score": 200,
                    "tier": "Enthusiast",
                    "streak": 1,
                },
                {
                    "PK": "ROOM#room123",
                    "SK": "PLAYER#user3",
                    "user_id": "user3",
                    "name": "Charlie",
                    "score": 300,
                    "tier": "Amateur",
                    "streak": 2,
                },
            ]
        },
    ]

    # Save updated room with different players
    room2 = Room(
        room_id="room123",
        players=(
            Player(user_id="user2", name="Bob", score=200, tier="Enthusiast", streak=1),
            Player(user_id="user3", name="Charlie", score=300, tier="Amateur", streak=2),
        ),
        status="waiting",
        created_at=1000000,
    )
    await repository.save(room2)

    # Get
    retrieved = await repository.get("room123")

    # Verify new state
    assert retrieved is not None
    assert len(retrieved.players) == 2
    assert retrieved.status == "waiting"
    player_ids = {p.user_id for p in retrieved.players}
    assert player_ids == {"user2", "user3"}
    assert "user1" not in player_ids


@pytest.mark.asyncio
async def test_list_by_status_returns_matching_rooms(repository: RoomRepositoryDDB, mock_table):
    """Test list_by_status returns only rooms with matching status."""
    # Mock GSI query to return metadata items
    mock_table.query.side_effect = [
        # First call: GSI query for active rooms
        {
            "Items": [
                {
                    "PK": "ROOM#room1",
                    "SK": "METADATA",
                    "status": "active",
                    "created_at": 1000000,
                    "GSI1_PK": "STATUS#active",
                    "GSI1_SK": 1000000,
                },
                {
                    "PK": "ROOM#room2",
                    "SK": "METADATA",
                    "status": "active",
                    "created_at": 2000000,
                    "GSI1_PK": "STATUS#active",
                    "GSI1_SK": 2000000,
                },
            ]
        },
        # Subsequent calls: get each room
        {
            "Items": [
                {
                    "PK": "ROOM#room1",
                    "SK": "METADATA",
                    "status": "active",
                    "created_at": 1000000,
                }
            ]
        },
        {
            "Items": [
                {
                    "PK": "ROOM#room2",
                    "SK": "METADATA",
                    "status": "active",
                    "created_at": 2000000,
                }
            ]
        },
    ]

    # List active rooms
    active_rooms = await repository.list_by_status("active")

    assert len(active_rooms) == 2
    room_ids = {r.room_id for r in active_rooms}
    assert room_ids == {"room1", "room2"}


@pytest.mark.asyncio
async def test_list_by_status_sorted_by_created_at(repository: RoomRepositoryDDB, mock_table):
    """Test list_by_status returns rooms sorted by created_at ascending."""
    # Mock GSI query to return metadata items in sorted order
    mock_table.query.side_effect = [
        # First call: GSI query (already sorted by GSI1_SK)
        {
            "Items": [
                {
                    "PK": "ROOM#room2",
                    "SK": "METADATA",
                    "status": "active",
                    "created_at": 1000000,
                    "GSI1_PK": "STATUS#active",
                    "GSI1_SK": 1000000,
                },
                {
                    "PK": "ROOM#room3",
                    "SK": "METADATA",
                    "status": "active",
                    "created_at": 2000000,
                    "GSI1_PK": "STATUS#active",
                    "GSI1_SK": 2000000,
                },
                {
                    "PK": "ROOM#room1",
                    "SK": "METADATA",
                    "status": "active",
                    "created_at": 3000000,
                    "GSI1_PK": "STATUS#active",
                    "GSI1_SK": 3000000,
                },
            ]
        },
        # Subsequent calls: get each room
        {
            "Items": [
                {"PK": "ROOM#room2", "SK": "METADATA", "status": "active", "created_at": 1000000}
            ]
        },
        {
            "Items": [
                {"PK": "ROOM#room3", "SK": "METADATA", "status": "active", "created_at": 2000000}
            ]
        },
        {
            "Items": [
                {"PK": "ROOM#room1", "SK": "METADATA", "status": "active", "created_at": 3000000}
            ]
        },
    ]

    # List
    rooms = await repository.list_by_status("active")

    # Verify sorted by created_at
    assert len(rooms) == 3
    assert rooms[0].room_id == "room2"  # created_at=1000000
    assert rooms[1].room_id == "room3"  # created_at=2000000
    assert rooms[2].room_id == "room1"  # created_at=3000000


@pytest.mark.asyncio
async def test_add_player_appends_to_room(repository: RoomRepositoryDDB, mock_table):
    """Test add_player adds player without affecting others."""
    # Mock put_item
    mock_table.put_item.return_value = None

    # Mock get to return room with two players
    mock_table.query.return_value = {
        "Items": [
            {
                "PK": "ROOM#room123",
                "SK": "METADATA",
                "status": "active",
                "created_at": 1000000,
            },
            {
                "PK": "ROOM#room123",
                "SK": "PLAYER#user1",
                "user_id": "user1",
                "name": "Alice",
                "score": 100,
                "tier": "Dummies",
                "streak": 0,
            },
            {
                "PK": "ROOM#room123",
                "SK": "PLAYER#user2",
                "user_id": "user2",
                "name": "Bob",
                "score": 200,
                "tier": "Enthusiast",
                "streak": 1,
            },
        ]
    }

    # Add second player
    new_player = Player(user_id="user2", name="Bob", score=200, tier="Enthusiast", streak=1)
    updated_room = await repository.add_player("room123", new_player)

    # Verify
    assert len(updated_room.players) == 2
    player_ids = {p.user_id for p in updated_room.players}
    assert player_ids == {"user1", "user2"}

    # Verify put_item was called
    mock_table.put_item.assert_called_once()


@pytest.mark.asyncio
async def test_remove_player_removes_one_player(repository: RoomRepositoryDDB, mock_table):
    """Test remove_player removes specified player without affecting others."""
    # Mock delete_item
    mock_table.delete_item.return_value = None

    # Mock get to return room with one player
    mock_table.query.return_value = {
        "Items": [
            {
                "PK": "ROOM#room123",
                "SK": "METADATA",
                "status": "active",
                "created_at": 1000000,
            },
            {
                "PK": "ROOM#room123",
                "SK": "PLAYER#user2",
                "user_id": "user2",
                "name": "Bob",
                "score": 200,
                "tier": "Enthusiast",
                "streak": 1,
            },
        ]
    }

    # Remove one player
    updated_room = await repository.remove_player("room123", "user1")

    # Verify
    assert len(updated_room.players) == 1
    assert updated_room.players[0].user_id == "user2"
    assert updated_room.players[0].name == "Bob"

    # Verify delete_item was called
    mock_table.delete_item.assert_called_once()


@pytest.mark.asyncio
async def test_delete_removes_entire_room(repository: RoomRepositoryDDB, mock_table):
    """Test delete removes room metadata and all players."""
    # Mock query to return room items
    mock_table.query.return_value = {
        "Items": [
            {"PK": "ROOM#room123", "SK": "METADATA"},
            {"PK": "ROOM#room123", "SK": "PLAYER#user1"},
            {"PK": "ROOM#room123", "SK": "PLAYER#user2"},
        ]
    }

    # Delete
    await repository.delete("room123")

    # Verify batch_writer was used
    assert mock_table.batch_writer.called


@pytest.mark.asyncio
async def test_delete_nonexistent_room_is_noop(repository: RoomRepositoryDDB, mock_table):
    """Test deleting nonexistent room doesn't raise error."""
    # Mock empty query response
    mock_table.query.return_value = {"Items": []}

    # Should not raise
    await repository.delete("nonexistent")


@pytest.mark.asyncio
async def test_add_player_to_nonexistent_room_raises(repository: RoomRepositoryDDB, mock_table):
    """Test add_player raises ValueError for nonexistent room."""
    # Mock put_item
    mock_table.put_item.return_value = None

    # Mock get to return None (room not found)
    mock_table.query.return_value = {"Items": []}

    player = Player(user_id="user1", name="Alice", score=0, tier="Dummies", streak=0)

    with pytest.raises(ValueError, match="Room nonexistent not found"):
        await repository.add_player("nonexistent", player)


@pytest.mark.asyncio
async def test_remove_player_from_nonexistent_room_raises(
    repository: RoomRepositoryDDB, mock_table
):
    """Test remove_player raises ValueError for nonexistent room."""
    # Mock delete_item
    mock_table.delete_item.return_value = None

    # Mock get to return None (room not found)
    mock_table.query.return_value = {"Items": []}

    with pytest.raises(ValueError, match="Room nonexistent not found"):
        await repository.remove_player("nonexistent", "user1")
