"""Tests for DynamoDB Connection Repository."""

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.dynamodb.connection_repository_ddb import ConnectionRepositoryDDB


@pytest.fixture
def mock_table():
    """Create a mock DynamoDB table."""
    table = AsyncMock()
    table.get_item = AsyncMock()
    table.put_item = AsyncMock()
    table.update_item = AsyncMock()
    table.delete_item = AsyncMock()
    table.query = AsyncMock()
    return table


@pytest.fixture
def repository(mock_table):
    """Create repository instance with mocked table."""
    repo = ConnectionRepositoryDDB(
        table_name="test-table",
        region="eu-central-1",
        ttl_seconds=3600,
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
async def test_put_creates_connection_with_ttl(repository: ConnectionRepositoryDDB, mock_table):
    """Test put creates connection with TTL."""
    mock_table.put_item.return_value = None
    
    await repository.put(
        conn_id="conn123",
        user_id="user1",
        room_id="room456",
        connected_at_ms=1000000000,
    )
    
    # Verify put_item was called with correct data
    mock_table.put_item.assert_called_once()
    call_kwargs = mock_table.put_item.call_args[1]
    item = call_kwargs["Item"]
    
    assert item["PK"] == "CONN#conn123"
    assert item["SK"] == "METADATA"
    assert item["conn_id"] == "conn123"
    assert item["user_id"] == "user1"
    assert item["room_id"] == "room456"
    assert item["connected_at_ms"] == 1000000000
    assert item["ttl"] == 1000000 + 3600  # (connected_at_ms // 1000) + ttl_seconds
    assert item["GSI1_PK"] == "ROOM#room456"
    assert item["GSI1_SK"] == 1000000000


@pytest.mark.asyncio
async def test_put_calculates_ttl_correctly(repository: ConnectionRepositoryDDB, mock_table):
    """Test put calculates TTL in epoch seconds."""
    mock_table.put_item.return_value = None
    
    # connected_at_ms = 1500000000 ms = 1500000 seconds
    # ttl = 1500000 + 3600 = 1503600
    await repository.put(
        conn_id="conn123",
        user_id="user1",
        room_id="room456",
        connected_at_ms=1500000000,
    )
    
    call_kwargs = mock_table.put_item.call_args[1]
    item = call_kwargs["Item"]
    
    assert item["ttl"] == 1503600


@pytest.mark.asyncio
async def test_get_returns_none_when_connection_not_found(repository: ConnectionRepositoryDDB, mock_table):
    """Test get returns None for nonexistent connection."""
    # Mock empty response
    mock_table.get_item.return_value = {}
    
    conn = await repository.get("nonexistent")
    assert conn is None
    
    # Verify get_item was called with correct keys
    mock_table.get_item.assert_called_once()
    call_kwargs = mock_table.get_item.call_args[1]
    assert call_kwargs["Key"]["PK"] == "CONN#nonexistent"
    assert call_kwargs["Key"]["SK"] == "METADATA"


@pytest.mark.asyncio
async def test_get_returns_connection_when_found(repository: ConnectionRepositoryDDB, mock_table):
    """Test get returns connection with all fields."""
    # Mock response with connection data
    mock_table.get_item.return_value = {
        "Item": {
            "PK": "CONN#conn123",
            "SK": "METADATA",
            "conn_id": "conn123",
            "user_id": "user1",
            "room_id": "room456",
            "connected_at_ms": 1000000000,
            "ttl": 1003600,
        }
    }
    
    conn = await repository.get("conn123")
    
    assert conn is not None
    assert conn["conn_id"] == "conn123"
    assert conn["user_id"] == "user1"
    assert conn["room_id"] == "room456"
    assert conn["connected_at_ms"] == 1000000000
    # TTL is not returned (internal field)
    assert "ttl" not in conn


@pytest.mark.asyncio
async def test_delete_removes_connection(repository: ConnectionRepositoryDDB, mock_table):
    """Test delete removes connection."""
    mock_table.delete_item.return_value = None
    
    await repository.delete("conn123")
    
    # Verify delete_item was called with correct keys
    mock_table.delete_item.assert_called_once()
    call_kwargs = mock_table.delete_item.call_args[1]
    assert call_kwargs["Key"]["PK"] == "CONN#conn123"
    assert call_kwargs["Key"]["SK"] == "METADATA"


@pytest.mark.asyncio
async def test_delete_nonexistent_connection_is_noop(repository: ConnectionRepositoryDDB, mock_table):
    """Test deleting nonexistent connection doesn't raise error."""
    mock_table.delete_item.return_value = None
    
    # Should not raise
    await repository.delete("nonexistent")


@pytest.mark.asyncio
async def test_list_by_room_returns_all_connections(repository: ConnectionRepositoryDDB, mock_table):
    """Test list_by_room returns all connections in a room."""
    # Mock GSI query
    mock_table.query.return_value = {
        "Items": [
            {
                "PK": "CONN#conn1",
                "SK": "METADATA",
                "conn_id": "conn1",
                "user_id": "user1",
                "room_id": "room456",
                "connected_at_ms": 1000000000,
            },
            {
                "PK": "CONN#conn2",
                "SK": "METADATA",
                "conn_id": "conn2",
                "user_id": "user2",
                "room_id": "room456",
                "connected_at_ms": 1000001000,
            },
            {
                "PK": "CONN#conn3",
                "SK": "METADATA",
                "conn_id": "conn3",
                "user_id": "user3",
                "room_id": "room456",
                "connected_at_ms": 1000002000,
            },
        ]
    }
    
    connections = await repository.list_by_room("room456")
    
    assert len(connections) == 3
    assert connections[0]["conn_id"] == "conn1"
    assert connections[0]["user_id"] == "user1"
    assert connections[1]["conn_id"] == "conn2"
    assert connections[1]["user_id"] == "user2"
    assert connections[2]["conn_id"] == "conn3"
    assert connections[2]["user_id"] == "user3"
    
    # Verify GSI query was called
    mock_table.query.assert_called_once()
    call_kwargs = mock_table.query.call_args[1]
    assert call_kwargs["IndexName"] == "GSI1"
    assert call_kwargs["ExpressionAttributeValues"][":gsi1_pk"] == "ROOM#room456"
    assert call_kwargs["ScanIndexForward"] is True  # Ascending order


@pytest.mark.asyncio
async def test_list_by_room_returns_empty_list_when_no_connections(repository: ConnectionRepositoryDDB, mock_table):
    """Test list_by_room returns empty list when room has no connections."""
    # Mock empty GSI query
    mock_table.query.return_value = {"Items": []}
    
    connections = await repository.list_by_room("empty_room")
    
    assert connections == []


@pytest.mark.asyncio
async def test_update_room_changes_room_id(repository: ConnectionRepositoryDDB, mock_table):
    """Test update_room changes the room_id and GSI1_PK."""
    # Mock get to return existing connection
    mock_table.get_item.return_value = {
        "Item": {
            "PK": "CONN#conn123",
            "SK": "METADATA",
            "conn_id": "conn123",
            "user_id": "user1",
            "room_id": "room456",
            "connected_at_ms": 1000000000,
        }
    }
    
    mock_table.update_item.return_value = None
    
    await repository.update_room("conn123", "room789")
    
    # Verify update_item was called with correct parameters
    mock_table.update_item.assert_called_once()
    call_kwargs = mock_table.update_item.call_args[1]
    
    assert call_kwargs["Key"]["PK"] == "CONN#conn123"
    assert call_kwargs["Key"]["SK"] == "METADATA"
    assert call_kwargs["UpdateExpression"] == "SET room_id = :room_id, GSI1_PK = :gsi1_pk"
    assert call_kwargs["ExpressionAttributeValues"][":room_id"] == "room789"
    assert call_kwargs["ExpressionAttributeValues"][":gsi1_pk"] == "ROOM#room789"
    assert "ConditionExpression" in call_kwargs  # Ensures connection exists


@pytest.mark.asyncio
async def test_update_room_raises_when_connection_not_found(repository: ConnectionRepositoryDDB, mock_table):
    """Test update_room raises ValueError when connection doesn't exist."""
    # Mock get to return None
    mock_table.get_item.return_value = {}
    
    with pytest.raises(ValueError, match="Connection nonexistent not found"):
        await repository.update_room("nonexistent", "room789")


@pytest.mark.asyncio
async def test_list_by_room_sorted_by_connected_at(repository: ConnectionRepositoryDDB, mock_table):
    """Test list_by_room returns connections sorted by connected_at_ms."""
    # Mock GSI query (already sorted by GSI1_SK = connected_at_ms)
    mock_table.query.return_value = {
        "Items": [
            {
                "conn_id": "conn2",
                "user_id": "user2",
                "room_id": "room456",
                "connected_at_ms": 1000000000,
            },
            {
                "conn_id": "conn1",
                "user_id": "user1",
                "room_id": "room456",
                "connected_at_ms": 1000001000,
            },
            {
                "conn_id": "conn3",
                "user_id": "user3",
                "room_id": "room456",
                "connected_at_ms": 1000002000,
            },
        ]
    }
    
    connections = await repository.list_by_room("room456")
    
    # Verify order is preserved (earliest connection first)
    assert connections[0]["conn_id"] == "conn2"
    assert connections[0]["connected_at_ms"] == 1000000000
    assert connections[1]["conn_id"] == "conn1"
    assert connections[1]["connected_at_ms"] == 1000001000
    assert connections[2]["conn_id"] == "conn3"
    assert connections[2]["connected_at_ms"] == 1000002000
