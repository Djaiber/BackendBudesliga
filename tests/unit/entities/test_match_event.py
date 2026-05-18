"""Tests for MatchEvent entity."""

import pytest

from src.domain.entities import MatchEvent


def test_match_event_happy_path() -> None:
    """Test creating a valid match event."""
    event = MatchEvent(
        event_id="evt-123",
        minute=45,
        second=30,
        event_type="GOAL",
        team="team-a",
        player="player-1",
        x_position=50.5,
        y_position=30.2,
        metadata={"assist": "player-2"},
    )

    assert event.event_id == "evt-123"
    assert event.minute == 45
    assert event.second == 30
    assert event.event_type == "GOAL"


def test_match_event_minute_too_low() -> None:
    """Test that minute < 0 raises ValueError."""
    with pytest.raises(ValueError, match="minute must be 0-120"):
        MatchEvent(
            event_id="evt-123",
            minute=-1,
            second=0,
            event_type="GOAL",
            team="team-a",
            player=None,
            x_position=None,
            y_position=None,
            metadata={},
        )


def test_match_event_minute_too_high() -> None:
    """Test that minute > 120 raises ValueError."""
    with pytest.raises(ValueError, match="minute must be 0-120"):
        MatchEvent(
            event_id="evt-123",
            minute=121,
            second=0,
            event_type="GOAL",
            team="team-a",
            player=None,
            x_position=None,
            y_position=None,
            metadata={},
        )


def test_match_event_second_too_low() -> None:
    """Test that second < 0 raises ValueError."""
    with pytest.raises(ValueError, match="second must be 0-59"):
        MatchEvent(
            event_id="evt-123",
            minute=0,
            second=-1,
            event_type="GOAL",
            team="team-a",
            player=None,
            x_position=None,
            y_position=None,
            metadata={},
        )


def test_match_event_second_too_high() -> None:
    """Test that second > 59 raises ValueError."""
    with pytest.raises(ValueError, match="second must be 0-59"):
        MatchEvent(
            event_id="evt-123",
            minute=0,
            second=60,
            event_type="GOAL",
            team="team-a",
            player=None,
            x_position=None,
            y_position=None,
            metadata={},
        )


def test_match_event_invalid_event_type() -> None:
    """Test that invalid event_type raises ValueError."""
    with pytest.raises(ValueError, match="event_type must be one of"):
        MatchEvent(
            event_id="evt-123",
            minute=0,
            second=0,
            event_type="INVALID_TYPE",
            team="team-a",
            player=None,
            x_position=None,
            y_position=None,
            metadata={},
        )


def test_match_event_is_frozen() -> None:
    """Test that MatchEvent is immutable."""
    event = MatchEvent(
        event_id="evt-123",
        minute=0,
        second=0,
        event_type="GOAL",
        team="team-a",
        player=None,
        x_position=None,
        y_position=None,
        metadata={},
    )

    with pytest.raises(Exception):  # FrozenInstanceError
        event.minute = 10  # type: ignore[misc]
