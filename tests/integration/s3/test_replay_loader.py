"""Tests for S3 Replay Loader."""

import json
from unittest.mock import AsyncMock

import pytest

from src.domain.entities import MatchEvent
from src.infrastructure.s3.replay_loader import ReplayLoader


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    client = AsyncMock()
    client.get_object = AsyncMock()
    return client


@pytest.fixture
def loader(mock_s3_client):
    """Create loader instance with mocked client."""
    ldr = ReplayLoader(
        bucket="test-replay-bucket",
        region="eu-central-1",
        enable_cache=True,
    )

    # Create a mock client that acts as an async context manager
    mock_client_cm = AsyncMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_client_cm.__aexit__ = AsyncMock(return_value=None)

    # Patch the session.client to return the mock
    def mock_client(*args, **kwargs):
        return mock_client_cm

    ldr._session.client = mock_client
    return ldr


@pytest.fixture
def sample_events_json():
    """Sample events JSON data."""
    return [
        {
            "event_id": "evt-001",
            "minute": 0,
            "second": 0,
            "event_type": "KICK_OFF",
            "team": "team-a",
            "player": "player-1",
            "x_position": 50.0,
            "y_position": 50.0,
            "metadata": {"game_section": "firstHalf"},
        },
        {
            "event_id": "evt-002",
            "minute": 1,
            "second": 30,
            "event_type": "PASS",
            "team": "team-a",
            "player": "player-2",
            "x_position": 45.0,
            "y_position": 55.0,
            "metadata": {"recipient": "player-3"},
        },
        {
            "event_id": "evt-003",
            "minute": 5,
            "second": 15,
            "event_type": "GOAL",
            "team": "team-b",
            "player": "player-4",
            "x_position": 10.0,
            "y_position": 50.0,
            "metadata": {"assist": "player-5"},
        },
    ]


@pytest.mark.asyncio
async def test_load_events_from_s3(loader: ReplayLoader, mock_s3_client, sample_events_json):
    """Test loading events from S3."""
    # Mock S3 response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(sample_events_json).encode("utf-8"))
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Load events
    events = await loader.load_events("events.json")

    # Verify S3 call
    mock_s3_client.get_object.assert_called_once_with(
        Bucket="test-replay-bucket",
        Key="events.json",
    )

    # Verify events
    assert len(events) == 3
    assert all(isinstance(e, MatchEvent) for e in events)

    assert events[0].event_id == "evt-001"
    assert events[0].event_type == "KICK_OFF"
    assert events[0].minute == 0
    assert events[0].second == 0

    assert events[1].event_id == "evt-002"
    assert events[1].event_type == "PASS"
    assert events[1].minute == 1
    assert events[1].second == 30

    assert events[2].event_id == "evt-003"
    assert events[2].event_type == "GOAL"
    assert events[2].minute == 5
    assert events[2].second == 15


@pytest.mark.asyncio
async def test_load_events_caches_result(loader: ReplayLoader, mock_s3_client, sample_events_json):
    """Test that loaded events are cached."""
    # Mock S3 response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(sample_events_json).encode("utf-8"))
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Load events twice
    events1 = await loader.load_events("events.json")
    events2 = await loader.load_events("events.json")

    # S3 should only be called once (second call uses cache)
    assert mock_s3_client.get_object.call_count == 1

    # Both results should be the same
    assert len(events1) == len(events2) == 3
    assert events1[0].event_id == events2[0].event_id


@pytest.mark.asyncio
async def test_load_events_with_cache_disabled(mock_s3_client, sample_events_json):
    """Test loading events with caching disabled."""
    # Create loader with cache disabled
    loader = ReplayLoader(
        bucket="test-replay-bucket",
        region="eu-central-1",
        enable_cache=False,
    )

    # Mock client setup
    mock_client_cm = AsyncMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_s3_client)
    mock_client_cm.__aexit__ = AsyncMock(return_value=None)
    loader._session.client = lambda *args, **kwargs: mock_client_cm

    # Mock S3 response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(sample_events_json).encode("utf-8"))
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Load events twice
    await loader.load_events("events.json")
    await loader.load_events("events.json")

    # S3 should be called twice (no caching)
    assert mock_s3_client.get_object.call_count == 2


@pytest.mark.asyncio
async def test_load_events_handles_optional_fields(loader: ReplayLoader, mock_s3_client):
    """Test loading events with optional fields missing."""
    events_json = [
        {
            "event_id": "evt-001",
            "minute": 0,
            "second": 0,
            "event_type": "KICK_OFF",
            # team, player, x_position, y_position, metadata are optional
        }
    ]

    # Mock S3 response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(events_json).encode("utf-8"))
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Load events
    events = await loader.load_events("events.json")

    assert len(events) == 1
    assert events[0].event_id == "evt-001"
    assert events[0].team is None
    assert events[0].player is None
    assert events[0].x_position is None
    assert events[0].y_position is None
    assert events[0].metadata == {}


@pytest.mark.asyncio
async def test_load_events_skips_invalid_events(loader: ReplayLoader, mock_s3_client):
    """Test that invalid events are skipped with warning."""
    events_json = [
        {
            "event_id": "evt-001",
            "minute": 0,
            "second": 0,
            "event_type": "KICK_OFF",
        },
        {
            # Missing required fields
            "event_id": "evt-002",
            "minute": 1,
            # missing second and event_type
        },
        {
            "event_id": "evt-003",
            "minute": 2,
            "second": 0,
            "event_type": "PASS",
        },
    ]

    # Mock S3 response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(events_json).encode("utf-8"))
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Load events
    events = await loader.load_events("events.json")

    # Only valid events should be loaded
    assert len(events) == 2
    assert events[0].event_id == "evt-001"
    assert events[1].event_id == "evt-003"


@pytest.mark.asyncio
async def test_load_events_raises_on_invalid_json_format(loader: ReplayLoader, mock_s3_client):
    """Test that non-array JSON raises ValueError."""
    # Mock S3 response with object instead of array
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=b'{"not": "an array"}')
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Should raise ValueError
    with pytest.raises(RuntimeError, match="Failed to load events from S3"):
        await loader.load_events("events.json")


@pytest.mark.asyncio
async def test_load_events_raises_on_s3_error(loader: ReplayLoader, mock_s3_client):
    """Test that S3 errors are wrapped in RuntimeError."""
    # Mock S3 error
    mock_s3_client.get_object.side_effect = Exception("S3 connection failed")

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Failed to load events from S3"):
        await loader.load_events("events.json")


@pytest.mark.asyncio
async def test_load_match_info_from_s3(loader: ReplayLoader, mock_s3_client):
    """Test loading match info from S3."""
    match_info = {
        "match_id": "match-123",
        "teams": {
            "home": "Team A",
            "away": "Team B",
        },
        "date": "2024-01-15",
    }

    # Mock S3 response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(match_info).encode("utf-8"))
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Load match info
    info = await loader.load_match_info("match_info.json")

    # Verify S3 call
    mock_s3_client.get_object.assert_called_once_with(
        Bucket="test-replay-bucket",
        Key="match_info.json",
    )

    # Verify data
    assert info["match_id"] == "match-123"
    assert info["teams"]["home"] == "Team A"
    assert info["teams"]["away"] == "Team B"


@pytest.mark.asyncio
async def test_load_match_info_raises_on_s3_error(loader: ReplayLoader, mock_s3_client):
    """Test that S3 errors are wrapped in RuntimeError."""
    # Mock S3 error
    mock_s3_client.get_object.side_effect = Exception("S3 connection failed")

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Failed to load match info from S3"):
        await loader.load_match_info("match_info.json")


@pytest.mark.asyncio
async def test_clear_cache(loader: ReplayLoader, mock_s3_client, sample_events_json):
    """Test clearing the cache."""
    # Mock S3 response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(sample_events_json).encode("utf-8"))
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Load events to populate cache
    await loader.load_events("events.json")
    assert loader.get_cache_size() == 1

    # Clear cache
    loader.clear_cache()
    assert loader.get_cache_size() == 0

    # Next load should hit S3 again
    await loader.load_events("events.json")
    assert mock_s3_client.get_object.call_count == 2


@pytest.mark.asyncio
async def test_get_cache_size(loader: ReplayLoader, mock_s3_client, sample_events_json):
    """Test getting cache size."""
    # Mock S3 response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(sample_events_json).encode("utf-8"))
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Initially empty
    assert loader.get_cache_size() == 0

    # Load one key
    await loader.load_events("events1.json")
    assert loader.get_cache_size() == 1

    # Load another key
    await loader.load_events("events2.json")
    assert loader.get_cache_size() == 2


@pytest.mark.asyncio
async def test_loader_with_endpoint_url():
    """Test loader can be configured with endpoint URL for localstack."""
    loader = ReplayLoader(
        bucket="test-bucket",
        region="eu-central-1",
        endpoint_url="http://localhost:4566",
    )

    # Verify endpoint_url is stored
    assert loader._endpoint_url == "http://localhost:4566"


@pytest.mark.asyncio
async def test_load_events_with_complex_metadata(loader: ReplayLoader, mock_s3_client):
    """Test loading events with complex nested metadata."""
    events_json = [
        {
            "event_id": "evt-001",
            "minute": 0,
            "second": 0,
            "event_type": "PASS",
            "team": "team-a",
            "player": "player-1",
            "x_position": 50.0,
            "y_position": 50.0,
            "metadata": {
                "recipient": "player-2",
                "pass_type": "long",
                "evaluation": "successful",
                "nested": {
                    "key1": "value1",
                    "key2": [1, 2, 3],
                },
            },
        }
    ]

    # Mock S3 response
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(events_json).encode("utf-8"))
    body_mock.__aenter__ = AsyncMock(return_value=body_mock)
    body_mock.__aexit__ = AsyncMock(return_value=None)

    mock_s3_client.get_object.return_value = {"Body": body_mock}

    # Load events
    events = await loader.load_events("events.json")

    assert len(events) == 1
    assert events[0].metadata["recipient"] == "player-2"
    assert events[0].metadata["nested"]["key1"] == "value1"
    assert events[0].metadata["nested"]["key2"] == [1, 2, 3]
