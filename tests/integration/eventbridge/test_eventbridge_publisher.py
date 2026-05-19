"""Tests for EventBridge Publisher."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.eventbridge.eventbridge_publisher import EventBridgePublisher


@pytest.fixture
def mock_events_client():
    """Create a mock EventBridge client."""
    client = AsyncMock()
    client.put_events = AsyncMock()
    return client


@pytest.fixture
def publisher(mock_events_client):
    """Create publisher instance with mocked client."""
    pub = EventBridgePublisher(
        event_bus_name="test-event-bus",
        region="eu-central-1",
    )
    
    # Create a mock client that acts as an async context manager
    mock_client_cm = AsyncMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_events_client)
    mock_client_cm.__aexit__ = AsyncMock(return_value=None)
    
    # Patch the session.client to return the mock
    def mock_client(*args, **kwargs):
        return mock_client_cm
    
    pub._session.client = mock_client
    return pub


@pytest.mark.asyncio
async def test_publish_sends_event_to_eventbridge(publisher: EventBridgePublisher, mock_events_client):
    """Test publish sends event with correct structure."""
    # Mock successful response
    mock_events_client.put_events.return_value = {
        "FailedEntryCount": 0,
        "Entries": [{"EventId": "event-123"}],
    }
    
    await publisher.publish(
        source="connected-arena.game-engine",
        detail_type="PredictionWindowOpened",
        detail={"window_id": "win123", "room_id": "room456"},
    )
    
    # Verify put_events was called
    mock_events_client.put_events.assert_called_once()
    call_kwargs = mock_events_client.put_events.call_args[1]
    entries = call_kwargs["Entries"]
    
    assert len(entries) == 1
    entry = entries[0]
    
    assert entry["Source"] == "connected-arena.game-engine"
    assert entry["DetailType"] == "PredictionWindowOpened"
    assert entry["EventBusName"] == "test-event-bus"
    
    # Detail should be JSON string
    detail = json.loads(entry["Detail"])
    assert detail["window_id"] == "win123"
    assert detail["room_id"] == "room456"


@pytest.mark.asyncio
async def test_publish_serializes_detail_to_json(publisher: EventBridgePublisher, mock_events_client):
    """Test publish serializes detail dict to JSON string."""
    mock_events_client.put_events.return_value = {
        "FailedEntryCount": 0,
        "Entries": [{"EventId": "event-123"}],
    }
    
    detail = {
        "string_field": "value",
        "int_field": 42,
        "bool_field": True,
        "list_field": [1, 2, 3],
        "nested": {"key": "value"},
    }
    
    await publisher.publish(
        source="test.source",
        detail_type="TestEvent",
        detail=detail,
    )
    
    # Verify Detail is a JSON string
    call_kwargs = mock_events_client.put_events.call_args[1]
    entry = call_kwargs["Entries"][0]
    
    assert isinstance(entry["Detail"], str)
    parsed_detail = json.loads(entry["Detail"])
    assert parsed_detail == detail


@pytest.mark.asyncio
async def test_publish_raises_on_failed_entry(publisher: EventBridgePublisher, mock_events_client):
    """Test publish raises RuntimeError when EventBridge returns failure."""
    # Mock failed response
    mock_events_client.put_events.return_value = {
        "FailedEntryCount": 1,
        "Entries": [
            {
                "ErrorCode": "InternalException",
                "ErrorMessage": "Something went wrong",
            }
        ],
    }
    
    with pytest.raises(RuntimeError, match="Failed to publish event"):
        await publisher.publish(
            source="test.source",
            detail_type="TestEvent",
            detail={"key": "value"},
        )


@pytest.mark.asyncio
async def test_publish_handles_empty_detail(publisher: EventBridgePublisher, mock_events_client):
    """Test publish works with empty detail dict."""
    mock_events_client.put_events.return_value = {
        "FailedEntryCount": 0,
        "Entries": [{"EventId": "event-123"}],
    }
    
    await publisher.publish(
        source="test.source",
        detail_type="TestEvent",
        detail={},
    )
    
    # Verify Detail is empty JSON object
    call_kwargs = mock_events_client.put_events.call_args[1]
    entry = call_kwargs["Entries"][0]
    
    assert entry["Detail"] == "{}"


@pytest.mark.asyncio
async def test_publish_uses_configured_event_bus_name(publisher: EventBridgePublisher, mock_events_client):
    """Test publish uses the configured event bus name."""
    mock_events_client.put_events.return_value = {
        "FailedEntryCount": 0,
        "Entries": [{"EventId": "event-123"}],
    }
    
    await publisher.publish(
        source="test.source",
        detail_type="TestEvent",
        detail={"key": "value"},
    )
    
    # Verify EventBusName is set correctly
    call_kwargs = mock_events_client.put_events.call_args[1]
    entry = call_kwargs["Entries"][0]
    
    assert entry["EventBusName"] == "test-event-bus"


@pytest.mark.asyncio
async def test_publish_with_endpoint_url():
    """Test publisher can be configured with endpoint URL for localstack."""
    pub = EventBridgePublisher(
        event_bus_name="test-event-bus",
        region="eu-central-1",
        endpoint_url="http://localhost:4566",
    )
    
    # Verify endpoint_url is stored
    assert pub._endpoint_url == "http://localhost:4566"


@pytest.mark.asyncio
async def test_publish_handles_complex_nested_detail(publisher: EventBridgePublisher, mock_events_client):
    """Test publish handles complex nested detail structures."""
    mock_events_client.put_events.return_value = {
        "FailedEntryCount": 0,
        "Entries": [{"EventId": "event-123"}],
    }
    
    detail = {
        "window": {
            "id": "win123",
            "room_id": "room456",
            "options": ["A", "B", "C"],
            "metadata": {
                "created_by": "system",
                "timestamp": 1000000000,
            },
        },
        "players": [
            {"user_id": "user1", "score": 100},
            {"user_id": "user2", "score": 200},
        ],
    }
    
    await publisher.publish(
        source="test.source",
        detail_type="ComplexEvent",
        detail=detail,
    )
    
    # Verify Detail can be parsed back
    call_kwargs = mock_events_client.put_events.call_args[1]
    entry = call_kwargs["Entries"][0]
    
    parsed_detail = json.loads(entry["Detail"])
    assert parsed_detail == detail
    assert parsed_detail["window"]["options"] == ["A", "B", "C"]
    assert len(parsed_detail["players"]) == 2
