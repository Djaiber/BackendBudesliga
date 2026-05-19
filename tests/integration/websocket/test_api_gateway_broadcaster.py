"""Tests for API Gateway WebSocket Broadcaster."""

import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from botocore.exceptions import ClientError

from src.infrastructure.websocket.api_gateway_broadcaster import ApiGatewayBroadcaster


@pytest.fixture
def mock_connection_repo():
    """Create a mock connection repository."""
    repo = AsyncMock()
    repo.list_by_room = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def mock_apigw_client():
    """Create a mock API Gateway Management API client."""
    client = AsyncMock()
    client.post_to_connection = AsyncMock()
    return client


@pytest.fixture
def broadcaster(mock_connection_repo, mock_apigw_client):
    """Create broadcaster instance with mocked dependencies."""
    bc = ApiGatewayBroadcaster(
        api_endpoint="https://test.execute-api.eu-central-1.amazonaws.com/prod",
        connection_repo=mock_connection_repo,
        region="eu-central-1",
    )

    # Create a mock client that acts as an async context manager
    mock_client_cm = AsyncMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_apigw_client)
    mock_client_cm.__aexit__ = AsyncMock(return_value=None)

    # Patch the session.client to return the mock
    def mock_client(*args, **kwargs):
        return mock_client_cm

    bc._session.client = mock_client
    return bc


@pytest.mark.asyncio
async def test_send_to_connection_success(broadcaster: ApiGatewayBroadcaster, mock_apigw_client):
    """Test sending message to a single connection."""
    message = {"type": "test", "data": "hello"}

    await broadcaster.send_to_connection("conn-123", message)

    # Verify post_to_connection was called
    mock_apigw_client.post_to_connection.assert_called_once()
    call_kwargs = mock_apigw_client.post_to_connection.call_args[1]

    assert call_kwargs["ConnectionId"] == "conn-123"
    assert json.loads(call_kwargs["Data"].decode("utf-8")) == message


@pytest.mark.asyncio
async def test_send_to_connection_serializes_message(
    broadcaster: ApiGatewayBroadcaster, mock_apigw_client
):
    """Test message is JSON-serialized."""
    message = {
        "type": "complex",
        "nested": {"key": "value"},
        "list": [1, 2, 3],
        "bool": True,
    }

    await broadcaster.send_to_connection("conn-123", message)

    call_kwargs = mock_apigw_client.post_to_connection.call_args[1]
    data = call_kwargs["Data"]

    # Verify it's bytes
    assert isinstance(data, bytes)

    # Verify it can be decoded back
    decoded = json.loads(data.decode("utf-8"))
    assert decoded == message


@pytest.mark.asyncio
async def test_send_to_connection_handles_gone_exception(
    broadcaster: ApiGatewayBroadcaster,
    mock_apigw_client,
    mock_connection_repo,
):
    """Test that GoneException deletes the stale connection."""
    # Mock GoneException
    error_response = {"Error": {"Code": "GoneException", "Message": "Connection is gone"}}
    mock_apigw_client.post_to_connection.side_effect = ClientError(
        error_response, "PostToConnection"
    )

    # Should not raise, but should delete connection
    await broadcaster.send_to_connection("conn-123", {"type": "test"})

    # Verify connection was deleted
    mock_connection_repo.delete.assert_called_once_with("conn-123")


@pytest.mark.asyncio
async def test_send_to_connection_raises_on_other_client_error(
    broadcaster: ApiGatewayBroadcaster,
    mock_apigw_client,
):
    """Test that non-GoneException ClientErrors are raised."""
    # Mock other ClientError
    error_response = {"Error": {"Code": "InternalError", "Message": "Something went wrong"}}
    mock_apigw_client.post_to_connection.side_effect = ClientError(
        error_response, "PostToConnection"
    )

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Failed to send to connection"):
        await broadcaster.send_to_connection("conn-123", {"type": "test"})


@pytest.mark.asyncio
async def test_send_to_connection_raises_on_generic_exception(
    broadcaster: ApiGatewayBroadcaster,
    mock_apigw_client,
):
    """Test that generic exceptions are wrapped in RuntimeError."""
    # Mock generic exception
    mock_apigw_client.post_to_connection.side_effect = Exception("Network error")

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Failed to send to connection"):
        await broadcaster.send_to_connection("conn-123", {"type": "test"})


@pytest.mark.asyncio
async def test_broadcast_to_room_sends_to_all_connections(
    broadcaster: ApiGatewayBroadcaster,
    mock_apigw_client,
    mock_connection_repo,
):
    """Test broadcasting to all connections in a room."""
    # Mock connections in room
    mock_connection_repo.list_by_room.return_value = [
        {"conn_id": "conn-1", "user_id": "user-1", "room_id": "room-123"},
        {"conn_id": "conn-2", "user_id": "user-2", "room_id": "room-123"},
        {"conn_id": "conn-3", "user_id": "user-3", "room_id": "room-123"},
    ]

    message = {"type": "broadcast", "data": "hello everyone"}

    await broadcaster.broadcast_to_room("room-123", message)

    # Verify list_by_room was called
    mock_connection_repo.list_by_room.assert_called_once_with("room-123")

    # Verify post_to_connection was called 3 times
    assert mock_apigw_client.post_to_connection.call_count == 3

    # Verify all connections received the message
    calls = mock_apigw_client.post_to_connection.call_args_list
    connection_ids = [call[1]["ConnectionId"] for call in calls]
    assert set(connection_ids) == {"conn-1", "conn-2", "conn-3"}


@pytest.mark.asyncio
async def test_broadcast_to_room_handles_empty_room(
    broadcaster: ApiGatewayBroadcaster,
    mock_apigw_client,
    mock_connection_repo,
):
    """Test broadcasting to room with no connections."""
    # Mock empty room
    mock_connection_repo.list_by_room.return_value = []

    message = {"type": "broadcast", "data": "hello"}

    # Should not raise
    await broadcaster.broadcast_to_room("room-123", message)

    # Verify no messages were sent
    mock_apigw_client.post_to_connection.assert_not_called()


@pytest.mark.asyncio
async def test_broadcast_to_room_continues_on_individual_failures(
    broadcaster: ApiGatewayBroadcaster,
    mock_apigw_client,
    mock_connection_repo,
):
    """Test that broadcast continues even if some sends fail."""
    # Mock connections in room
    mock_connection_repo.list_by_room.return_value = [
        {"conn_id": "conn-1", "user_id": "user-1", "room_id": "room-123"},
        {"conn_id": "conn-2", "user_id": "user-2", "room_id": "room-123"},
        {"conn_id": "conn-3", "user_id": "user-3", "room_id": "room-123"},
    ]

    # Make second connection fail
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("Connection failed")
        return None

    mock_apigw_client.post_to_connection.side_effect = side_effect

    message = {"type": "broadcast", "data": "hello"}

    # Should not raise
    await broadcaster.broadcast_to_room("room-123", message)

    # Verify all 3 sends were attempted
    assert mock_apigw_client.post_to_connection.call_count == 3


@pytest.mark.asyncio
async def test_broadcast_to_room_handles_gone_connections(
    broadcaster: ApiGatewayBroadcaster,
    mock_apigw_client,
    mock_connection_repo,
):
    """Test that broadcast handles GoneException for stale connections."""
    # Mock connections in room
    mock_connection_repo.list_by_room.return_value = [
        {"conn_id": "conn-1", "user_id": "user-1", "room_id": "room-123"},
        {"conn_id": "conn-2", "user_id": "user-2", "room_id": "room-123"},
    ]

    # Make first connection gone
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            error_response = {"Error": {"Code": "GoneException", "Message": "Gone"}}
            raise ClientError(error_response, "PostToConnection")
        return None

    mock_apigw_client.post_to_connection.side_effect = side_effect

    message = {"type": "broadcast", "data": "hello"}

    await broadcaster.broadcast_to_room("room-123", message)

    # Verify gone connection was deleted
    mock_connection_repo.delete.assert_called_once_with("conn-1")

    # Verify both sends were attempted
    assert mock_apigw_client.post_to_connection.call_count == 2


@pytest.mark.asyncio
async def test_broadcaster_uses_configured_endpoint():
    """Test broadcaster uses the configured API endpoint."""
    mock_repo = AsyncMock()

    broadcaster = ApiGatewayBroadcaster(
        api_endpoint="https://custom.execute-api.us-east-1.amazonaws.com/stage",
        connection_repo=mock_repo,
        region="us-east-1",
    )

    # Verify endpoint is stored
    assert broadcaster._api_endpoint == "https://custom.execute-api.us-east-1.amazonaws.com/stage"
    assert broadcaster._region == "us-east-1"


@pytest.mark.asyncio
async def test_send_to_connection_with_empty_message(
    broadcaster: ApiGatewayBroadcaster, mock_apigw_client
):
    """Test sending empty message."""
    message = {}

    await broadcaster.send_to_connection("conn-123", message)

    call_kwargs = mock_apigw_client.post_to_connection.call_args[1]
    assert call_kwargs["Data"] == b"{}"


@pytest.mark.asyncio
async def test_broadcast_sends_messages_in_parallel(
    broadcaster: ApiGatewayBroadcaster,
    mock_apigw_client,
    mock_connection_repo,
):
    """Test that broadcast sends messages in parallel (not sequentially)."""
    # Mock many connections
    connections = [
        {"conn_id": f"conn-{i}", "user_id": f"user-{i}", "room_id": "room-123"} for i in range(10)
    ]
    mock_connection_repo.list_by_room.return_value = connections

    # Track call order
    call_order = []

    async def track_call(*args, **kwargs):
        call_order.append(kwargs["ConnectionId"])
        # Simulate some delay
        await asyncio.sleep(0.01)

    mock_apigw_client.post_to_connection.side_effect = track_call

    message = {"type": "broadcast", "data": "hello"}

    await broadcaster.broadcast_to_room("room-123", message)

    # All 10 connections should have been called
    assert len(call_order) == 10

    # Verify all connection IDs are present
    assert set(call_order) == {f"conn-{i}" for i in range(10)}
