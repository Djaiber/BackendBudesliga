"""Tests for DynamoDB Score Repository."""

from unittest.mock import AsyncMock

import pytest

from src.domain.entities import Player, ScoreDelta
from src.infrastructure.dynamodb.score_repository_ddb import ScoreRepositoryDDB


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table."""
    table = AsyncMock()
    table.get_item = AsyncMock()
    table.put_item = AsyncMock()
    table.update_item = AsyncMock()
    table.query = AsyncMock()
    return table


@pytest.fixture
def repository(mock_table):
    """Create repository instance with mocked table."""
    repo = ScoreRepositoryDDB(
        table_name="test-table",
        region="eu-central-1",
    )

    # Create a mock resource that acts as an async context manager
    mock_ddb = AsyncMock()
    mock_ddb.Table = AsyncMock(return_value=mock_table)
    mock_ddb.__aenter__ = AsyncMock(return_value=mock_ddb)
    mock_ddb.__aexit__ = AsyncMock(return_value=None)

    # Patch the session.resource to return the mock directly
    def mock_resource(*args, **kwargs):
        return mock_ddb

    repo._session.resource = mock_resource
    return repo


@pytest.mark.asyncio
async def test_get_player_returns_none_when_not_found(repository: ScoreRepositoryDDB, mock_table):
    """Test get_player returns None for nonexistent player."""
    # Mock empty response
    mock_table.get_item.return_value = {}

    player = await repository.get_player("nonexistent")
    assert player is None

    # Verify get_item was called with correct keys
    mock_table.get_item.assert_called_once()
    call_kwargs = mock_table.get_item.call_args[1]
    assert call_kwargs["Key"]["PK"] == "USER#nonexistent"
    assert call_kwargs["Key"]["SK"] == "PROFILE"


@pytest.mark.asyncio
async def test_get_player_returns_player_when_found(repository: ScoreRepositoryDDB, mock_table):
    """Test get_player returns player with all fields."""
    # Mock response with player data
    mock_table.get_item.return_value = {
        "Item": {
            "PK": "USER#user1",
            "SK": "PROFILE",
            "user_id": "user1",
            "name": "Alice",
            "score": 100,
            "tier": "Dummies",
            "streak": 2,
        }
    }

    player = await repository.get_player("user1")

    assert player is not None
    assert player.user_id == "user1"
    assert player.name == "Alice"
    assert player.score == 100
    assert player.tier == "Dummies"
    assert player.streak == 2


@pytest.mark.asyncio
async def test_upsert_player_creates_new_player(repository: ScoreRepositoryDDB, mock_table):
    """Test upsert_player creates a new player."""
    player = Player(
        user_id="user1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=0,
    )

    mock_table.put_item.return_value = None

    await repository.upsert_player(player)

    # Verify put_item was called with correct data
    mock_table.put_item.assert_called_once()
    call_kwargs = mock_table.put_item.call_args[1]
    item = call_kwargs["Item"]

    assert item["PK"] == "USER#user1"
    assert item["SK"] == "PROFILE"
    assert item["user_id"] == "user1"
    assert item["name"] == "Alice"
    assert item["score"] == 0
    assert item["tier"] == "Dummies"
    assert item["streak"] == 0


@pytest.mark.asyncio
async def test_upsert_player_updates_existing_player(repository: ScoreRepositoryDDB, mock_table):
    """Test upsert_player overwrites existing player."""
    player = Player(
        user_id="user1",
        name="Alice Updated",
        score=200,
        tier="Enthusiast",
        streak=5,
    )

    mock_table.put_item.return_value = None

    await repository.upsert_player(player)

    # Verify put_item was called (put_item overwrites)
    mock_table.put_item.assert_called_once()
    call_kwargs = mock_table.put_item.call_args[1]
    item = call_kwargs["Item"]

    assert item["score"] == 200
    assert item["tier"] == "Enthusiast"
    assert item["streak"] == 5


@pytest.mark.asyncio
async def test_apply_delta_updates_player_atomically(repository: ScoreRepositoryDDB, mock_table):
    """Test apply_delta uses UpdateItem for atomic update."""
    delta = ScoreDelta(
        user_id="user1",
        points=50,
        new_score=150,
        new_streak=3,
        new_tier="Enthusiast",
        multiplier_applied=1.1,
    )

    # Mock update_item response
    mock_table.update_item.return_value = {
        "Attributes": {
            "PK": "USER#user1",
            "SK": "PROFILE",
            "user_id": "user1",
            "name": "Alice",
            "score": 150,
            "tier": "Enthusiast",
            "streak": 3,
        }
    }

    updated_player = await repository.apply_delta(delta)

    # Verify update_item was called with correct parameters
    mock_table.update_item.assert_called_once()
    call_kwargs = mock_table.update_item.call_args[1]

    assert call_kwargs["Key"]["PK"] == "USER#user1"
    assert call_kwargs["Key"]["SK"] == "PROFILE"
    assert call_kwargs["UpdateExpression"] == "SET score = :score, streak = :streak, tier = :tier"
    assert call_kwargs["ExpressionAttributeValues"][":score"] == 150
    assert call_kwargs["ExpressionAttributeValues"][":streak"] == 3
    assert call_kwargs["ExpressionAttributeValues"][":tier"] == "Enthusiast"
    assert "ConditionExpression" in call_kwargs  # Ensures player exists

    # Verify returned player
    assert updated_player.user_id == "user1"
    assert updated_player.score == 150
    assert updated_player.streak == 3
    assert updated_player.tier == "Enthusiast"


@pytest.mark.asyncio
async def test_apply_delta_handles_negative_points(repository: ScoreRepositoryDDB, mock_table):
    """Test apply_delta works with negative points (penalties)."""
    delta = ScoreDelta(
        user_id="user1",
        points=-20,
        new_score=80,
        new_streak=0,
        new_tier="Dummies",
        multiplier_applied=1.0,
    )

    mock_table.update_item.return_value = {
        "Attributes": {
            "PK": "USER#user1",
            "SK": "PROFILE",
            "user_id": "user1",
            "name": "Alice",
            "score": 80,
            "tier": "Dummies",
            "streak": 0,
        }
    }

    updated_player = await repository.apply_delta(delta)

    assert updated_player.score == 80
    assert updated_player.streak == 0
    assert updated_player.tier == "Dummies"


@pytest.mark.asyncio
async def test_leaderboard_returns_players_sorted_by_score(
    repository: ScoreRepositoryDDB, mock_table
):
    """Test leaderboard returns players sorted by score descending."""
    # Mock GSI query to return room membership items
    mock_table.query.side_effect = [
        # First call: GSI query for room members
        {
            "Items": [
                {"user_id": "user1", "GSI1_PK": "ROOM#room123", "GSI1_SK": 300},
                {"user_id": "user2", "GSI1_PK": "ROOM#room123", "GSI1_SK": 200},
                {"user_id": "user3", "GSI1_PK": "ROOM#room123", "GSI1_SK": 100},
            ]
        },
    ]

    # Mock get_item calls for each player
    mock_table.get_item.side_effect = [
        {
            "Item": {
                "user_id": "user1",
                "name": "Alice",
                "score": 300,
                "tier": "Savvy",
                "streak": 5,
            }
        },
        {
            "Item": {
                "user_id": "user2",
                "name": "Bob",
                "score": 200,
                "tier": "Amateur",
                "streak": 3,
            }
        },
        {
            "Item": {
                "user_id": "user3",
                "name": "Charlie",
                "score": 100,
                "tier": "Enthusiast",
                "streak": 1,
            }
        },
    ]

    leaderboard = await repository.leaderboard("room123")

    # Verify sorted by score descending
    assert len(leaderboard) == 3
    assert leaderboard[0].user_id == "user1"
    assert leaderboard[0].score == 300
    assert leaderboard[1].user_id == "user2"
    assert leaderboard[1].score == 200
    assert leaderboard[2].user_id == "user3"
    assert leaderboard[2].score == 100

    # Verify GSI query was called
    mock_table.query.assert_called_once()
    call_kwargs = mock_table.query.call_args[1]
    assert call_kwargs["IndexName"] == "GSI1"
    assert call_kwargs["ExpressionAttributeValues"][":gsi1_pk"] == "ROOM#room123"
    assert call_kwargs["ScanIndexForward"] is False  # Descending order


@pytest.mark.asyncio
async def test_leaderboard_returns_empty_list_for_empty_room(
    repository: ScoreRepositoryDDB, mock_table
):
    """Test leaderboard returns empty list when room has no players."""
    # Mock empty GSI query
    mock_table.query.return_value = {"Items": []}

    leaderboard = await repository.leaderboard("empty_room")

    assert leaderboard == []


@pytest.mark.asyncio
async def test_leaderboard_skips_players_not_found(repository: ScoreRepositoryDDB, mock_table):
    """Test leaderboard skips players whose profiles don't exist."""
    # Mock GSI query
    mock_table.query.return_value = {
        "Items": [
            {"user_id": "user1", "GSI1_PK": "ROOM#room123", "GSI1_SK": 200},
            {"user_id": "user2", "GSI1_PK": "ROOM#room123", "GSI1_SK": 100},
        ]
    }

    # Mock get_item: user1 exists, user2 doesn't
    mock_table.get_item.side_effect = [
        {
            "Item": {
                "user_id": "user1",
                "name": "Alice",
                "score": 200,
                "tier": "Amateur",
                "streak": 2,
            }
        },
        {},  # user2 not found
    ]

    leaderboard = await repository.leaderboard("room123")

    # Only user1 should be in leaderboard
    assert len(leaderboard) == 1
    assert leaderboard[0].user_id == "user1"
