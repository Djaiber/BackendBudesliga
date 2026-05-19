"""Tests for DynamoDB Window Repository."""

from unittest.mock import AsyncMock

import pytest

from src.domain.entities import Prediction, PredictionWindow
from src.infrastructure.dynamodb.window_repository_ddb import WindowRepositoryDDB


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
    repo = WindowRepositoryDDB(
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
async def test_get_returns_none_when_window_not_found(repository: WindowRepositoryDDB, mock_table):
    """Test get returns None for nonexistent window."""
    # Mock empty response
    mock_table.get_item.return_value = {}
    
    window = await repository.get("nonexistent")
    assert window is None
    
    # Verify get_item was called with correct keys
    mock_table.get_item.assert_called_once()
    call_kwargs = mock_table.get_item.call_args[1]
    assert call_kwargs["Key"]["PK"] == "WINDOW#nonexistent"
    assert call_kwargs["Key"]["SK"] == "METADATA"


@pytest.mark.asyncio
async def test_get_returns_window_with_options(repository: WindowRepositoryDDB, mock_table):
    """Test get returns window with all fields including options."""
    # Mock response with window data
    mock_table.get_item.return_value = {
        "Item": {
            "PK": "WINDOW#win1",
            "SK": "METADATA",
            "window_id": "win1",
            "room_id": "room123",
            "game": "NEXT_GOAL_TIMING",
            "prompt": "When will the next goal be scored?",
            "opened_at_ms": 1000000,
            "deadline_ms": 2000000,
            "options": ["0-15 min", "15-30 min", "30-45 min"],
            "status": "open",
        }
    }
    
    window = await repository.get("win1")
    
    assert window is not None
    assert window.window_id == "win1"
    assert window.room_id == "room123"
    assert window.game == "NEXT_GOAL_TIMING"
    assert window.prompt == "When will the next goal be scored?"
    assert window.opened_at_ms == 1000000
    assert window.deadline_ms == 2000000
    assert window.options == ("0-15 min", "15-30 min", "30-45 min")
    assert window.status == "open"


@pytest.mark.asyncio
async def test_get_returns_window_without_options(repository: WindowRepositoryDDB, mock_table):
    """Test get returns window when options is None."""
    # Mock response without options
    mock_table.get_item.return_value = {
        "Item": {
            "PK": "WINDOW#win1",
            "SK": "METADATA",
            "window_id": "win1",
            "room_id": "room123",
            "game": "CORNERS_IN_INTERVAL",
            "prompt": "How many corners in next 10 minutes?",
            "opened_at_ms": 1000000,
            "deadline_ms": 2000000,
            "status": "open",
        }
    }
    
    window = await repository.get("win1")
    
    assert window is not None
    assert window.options is None


@pytest.mark.asyncio
async def test_save_creates_window_with_options(repository: WindowRepositoryDDB, mock_table):
    """Test save creates window with options."""
    window = PredictionWindow(
        window_id="win1",
        room_id="room123",
        game="NEXT_GOAL_TIMING",
        prompt="When will the next goal be scored?",
        opened_at_ms=1000000,
        deadline_ms=2000000,
        options=("0-15 min", "15-30 min", "30-45 min"),
        status="open",
    )
    
    mock_table.put_item.return_value = None
    
    await repository.save(window)
    
    # Verify put_item was called with correct data
    mock_table.put_item.assert_called_once()
    call_kwargs = mock_table.put_item.call_args[1]
    item = call_kwargs["Item"]
    
    assert item["PK"] == "WINDOW#win1"
    assert item["SK"] == "METADATA"
    assert item["window_id"] == "win1"
    assert item["room_id"] == "room123"
    assert item["game"] == "NEXT_GOAL_TIMING"
    assert item["options"] == ["0-15 min", "15-30 min", "30-45 min"]  # Converted to list
    assert item["status"] == "open"
    assert item["GSI1_PK"] == "ROOM#room123"
    assert item["GSI1_SK"] == 1000000


@pytest.mark.asyncio
async def test_save_creates_window_without_options(repository: WindowRepositoryDDB, mock_table):
    """Test save creates window when options is None."""
    window = PredictionWindow(
        window_id="win1",
        room_id="room123",
        game="CORNERS_IN_INTERVAL",
        prompt="How many corners?",
        opened_at_ms=1000000,
        deadline_ms=2000000,
        options=None,
        status="open",
    )
    
    mock_table.put_item.return_value = None
    
    await repository.save(window)
    
    # Verify options is not in item
    call_kwargs = mock_table.put_item.call_args[1]
    item = call_kwargs["Item"]
    assert "options" not in item or item.get("options") is None


@pytest.mark.asyncio
async def test_list_open_by_room_returns_only_open_windows(repository: WindowRepositoryDDB, mock_table):
    """Test list_open_by_room returns only open windows for the room."""
    # Mock GSI query
    mock_table.query.return_value = {
        "Items": [
            {
                "PK": "WINDOW#win1",
                "SK": "METADATA",
                "window_id": "win1",
                "room_id": "room123",
                "game": "NEXT_GOAL_TIMING",
                "prompt": "Prompt 1",
                "opened_at_ms": 1000000,
                "deadline_ms": 2000000,
                "status": "open",
            },
            {
                "PK": "WINDOW#win2",
                "SK": "METADATA",
                "window_id": "win2",
                "room_id": "room123",
                "game": "CORNERS_IN_INTERVAL",
                "prompt": "Prompt 2",
                "opened_at_ms": 1500000,
                "deadline_ms": 2500000,
                "status": "closed",  # Should be filtered out
            },
            {
                "PK": "WINDOW#win3",
                "SK": "METADATA",
                "window_id": "win3",
                "room_id": "room123",
                "game": "GOAL_IN_TIME_WINDOW",
                "prompt": "Prompt 3",
                "opened_at_ms": 2000000,
                "deadline_ms": 3000000,
                "status": "open",
            },
        ]
    }
    
    windows = await repository.list_open_by_room("room123")
    
    # Only open windows should be returned
    assert len(windows) == 2
    assert windows[0].window_id == "win1"
    assert windows[0].status == "open"
    assert windows[1].window_id == "win3"
    assert windows[1].status == "open"
    
    # Verify GSI query was called
    mock_table.query.assert_called_once()
    call_kwargs = mock_table.query.call_args[1]
    assert call_kwargs["IndexName"] == "GSI1"
    assert call_kwargs["ExpressionAttributeValues"][":gsi1_pk"] == "ROOM#room123"
    assert call_kwargs["ScanIndexForward"] is True  # Ascending order


@pytest.mark.asyncio
async def test_list_open_by_room_returns_empty_list_when_no_open_windows(repository: WindowRepositoryDDB, mock_table):
    """Test list_open_by_room returns empty list when no open windows."""
    # Mock GSI query with only closed windows
    mock_table.query.return_value = {
        "Items": [
            {
                "PK": "WINDOW#win1",
                "SK": "METADATA",
                "window_id": "win1",
                "room_id": "room123",
                "game": "NEXT_GOAL_TIMING",
                "prompt": "Prompt 1",
                "opened_at_ms": 1000000,
                "deadline_ms": 2000000,
                "status": "closed",
            },
        ]
    }
    
    windows = await repository.list_open_by_room("room123")
    
    assert windows == []


@pytest.mark.asyncio
async def test_add_prediction_creates_submission_item(repository: WindowRepositoryDDB, mock_table):
    """Test add_prediction creates a submission item."""
    prediction = Prediction(
        window_id="win1",
        user_id="user1",
        value="0-15 min",
        submitted_at_ms=1500000,
    )
    
    mock_table.put_item.return_value = None
    
    await repository.add_prediction("win1", prediction)
    
    # Verify put_item was called with correct data
    mock_table.put_item.assert_called_once()
    call_kwargs = mock_table.put_item.call_args[1]
    item = call_kwargs["Item"]
    
    assert item["PK"] == "WINDOW#win1"
    assert item["SK"] == "SUBMISSION#user1"
    assert item["window_id"] == "win1"
    assert item["user_id"] == "user1"
    assert item["value"] == "0-15 min"
    assert item["submitted_at_ms"] == 1500000


@pytest.mark.asyncio
async def test_add_prediction_with_integer_value(repository: WindowRepositoryDDB, mock_table):
    """Test add_prediction works with integer values."""
    prediction = Prediction(
        window_id="win1",
        user_id="user1",
        value=3,  # Integer value
        submitted_at_ms=1500000,
    )
    
    mock_table.put_item.return_value = None
    
    await repository.add_prediction("win1", prediction)
    
    # Verify value is stored as integer
    call_kwargs = mock_table.put_item.call_args[1]
    item = call_kwargs["Item"]
    assert item["value"] == 3
    assert isinstance(item["value"], int)


@pytest.mark.asyncio
async def test_list_predictions_returns_all_submissions(repository: WindowRepositoryDDB, mock_table):
    """Test list_predictions returns all submissions for a window."""
    # Mock query response
    mock_table.query.return_value = {
        "Items": [
            {
                "PK": "WINDOW#win1",
                "SK": "SUBMISSION#user1",
                "window_id": "win1",
                "user_id": "user1",
                "value": "0-15 min",
                "submitted_at_ms": 1500000,
            },
            {
                "PK": "WINDOW#win1",
                "SK": "SUBMISSION#user2",
                "window_id": "win1",
                "user_id": "user2",
                "value": "15-30 min",
                "submitted_at_ms": 1600000,
            },
            {
                "PK": "WINDOW#win1",
                "SK": "SUBMISSION#user3",
                "window_id": "win1",
                "user_id": "user3",
                "value": 5,  # Integer value
                "submitted_at_ms": 1700000,
            },
        ]
    }
    
    predictions = await repository.list_predictions("win1")
    
    assert len(predictions) == 3
    assert predictions[0].user_id == "user1"
    assert predictions[0].value == "0-15 min"
    assert predictions[1].user_id == "user2"
    assert predictions[1].value == "15-30 min"
    assert predictions[2].user_id == "user3"
    assert predictions[2].value == 5
    
    # Verify query was called correctly
    mock_table.query.assert_called_once()
    call_kwargs = mock_table.query.call_args[1]
    assert call_kwargs["ExpressionAttributeValues"][":pk"] == "WINDOW#win1"
    assert call_kwargs["ExpressionAttributeValues"][":sk_prefix"] == "SUBMISSION#"


@pytest.mark.asyncio
async def test_list_predictions_returns_empty_list_when_no_submissions(repository: WindowRepositoryDDB, mock_table):
    """Test list_predictions returns empty list when no submissions."""
    # Mock empty query response
    mock_table.query.return_value = {"Items": []}
    
    predictions = await repository.list_predictions("win1")
    
    assert predictions == []


@pytest.mark.asyncio
async def test_close_updates_window_status(repository: WindowRepositoryDDB, mock_table):
    """Test close updates window status to closed."""
    mock_table.update_item.return_value = None
    
    await repository.close("win1", 2000000)
    
    # Verify update_item was called with correct parameters
    mock_table.update_item.assert_called_once()
    call_kwargs = mock_table.update_item.call_args[1]
    
    assert call_kwargs["Key"]["PK"] == "WINDOW#win1"
    assert call_kwargs["Key"]["SK"] == "METADATA"
    assert call_kwargs["UpdateExpression"] == "SET #status = :status"
    assert call_kwargs["ExpressionAttributeNames"]["#status"] == "status"
    assert call_kwargs["ExpressionAttributeValues"][":status"] == "closed"
    assert "ConditionExpression" in call_kwargs  # Ensures window exists
