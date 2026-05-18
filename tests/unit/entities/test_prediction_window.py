"""Tests for PredictionWindow entity."""

import pytest

from src.domain.entities import PredictionWindow


def test_prediction_window_happy_path() -> None:
    """Test creating a valid prediction window."""
    window = PredictionWindow(
        window_id="win-123",
        room_id="room-456",
        game=PredictionWindow.NEXT_GOAL_TIMING,
        prompt="When will the next goal be scored?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=("45", "50", "55", "60"),
        status=PredictionWindow.OPEN,
    )

    assert window.window_id == "win-123"
    assert window.game == PredictionWindow.NEXT_GOAL_TIMING
    assert window.status == PredictionWindow.OPEN


def test_prediction_window_deadline_before_opened() -> None:
    """Test that deadline_ms <= opened_at_ms raises ValueError."""
    with pytest.raises(ValueError, match="deadline_ms .* must be > opened_at_ms"):
        PredictionWindow(
            window_id="win-123",
            room_id="room-456",
            game=PredictionWindow.NEXT_GOAL_TIMING,
            prompt="Test",
            opened_at_ms=1020000,
            deadline_ms=1000000,
            options=None,
            status=PredictionWindow.OPEN,
        )


def test_prediction_window_deadline_equals_opened() -> None:
    """Test that deadline_ms == opened_at_ms raises ValueError."""
    with pytest.raises(ValueError, match="deadline_ms .* must be > opened_at_ms"):
        PredictionWindow(
            window_id="win-123",
            room_id="room-456",
            game=PredictionWindow.NEXT_GOAL_TIMING,
            prompt="Test",
            opened_at_ms=1000000,
            deadline_ms=1000000,
            options=None,
            status=PredictionWindow.OPEN,
        )


def test_prediction_window_invalid_game() -> None:
    """Test that invalid game raises ValueError."""
    with pytest.raises(ValueError, match="game must be one of"):
        PredictionWindow(
            window_id="win-123",
            room_id="room-456",
            game="INVALID_GAME",
            prompt="Test",
            opened_at_ms=1000000,
            deadline_ms=1020000,
            options=None,
            status=PredictionWindow.OPEN,
        )


def test_prediction_window_invalid_status() -> None:
    """Test that invalid status raises ValueError."""
    with pytest.raises(ValueError, match="status must be one of"):
        PredictionWindow(
            window_id="win-123",
            room_id="room-456",
            game=PredictionWindow.NEXT_GOAL_TIMING,
            prompt="Test",
            opened_at_ms=1000000,
            deadline_ms=1020000,
            options=None,
            status="invalid_status",
        )


def test_prediction_window_is_expired_true() -> None:
    """Test is_expired returns True when now >= deadline."""
    window = PredictionWindow(
        window_id="win-123",
        room_id="room-456",
        game=PredictionWindow.NEXT_GOAL_TIMING,
        prompt="Test",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    assert window.is_expired(1020000) is True
    assert window.is_expired(1030000) is True


def test_prediction_window_is_expired_false() -> None:
    """Test is_expired returns False when now < deadline."""
    window = PredictionWindow(
        window_id="win-123",
        room_id="room-456",
        game=PredictionWindow.NEXT_GOAL_TIMING,
        prompt="Test",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    assert window.is_expired(1010000) is False
    assert window.is_expired(1019999) is False


def test_prediction_window_is_frozen() -> None:
    """Test that PredictionWindow is immutable."""
    window = PredictionWindow(
        window_id="win-123",
        room_id="room-456",
        game=PredictionWindow.NEXT_GOAL_TIMING,
        prompt="Test",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    with pytest.raises(Exception):  # FrozenInstanceError
        window.status = PredictionWindow.CLOSED  # type: ignore[misc]
