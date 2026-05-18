"""Tests for Player entity."""

import pytest

from src.domain.entities import Player


def test_player_happy_path() -> None:
    """Test creating a valid player."""
    player = Player(
        user_id="user-123",
        name="John Doe",
        score=500,
        tier=Player.ENTHUSIAST,
        streak=3,
    )

    assert player.user_id == "user-123"
    assert player.name == "John Doe"
    assert player.score == 500
    assert player.tier == Player.ENTHUSIAST
    assert player.streak == 3


def test_player_score_negative() -> None:
    """Test that negative score raises ValueError."""
    with pytest.raises(ValueError, match="score must be >= 0"):
        Player(
            user_id="user-123",
            name="John Doe",
            score=-1,
            tier=Player.DUMMIES,
            streak=0,
        )


def test_player_streak_negative() -> None:
    """Test that negative streak raises ValueError."""
    with pytest.raises(ValueError, match="streak must be >= 0"):
        Player(
            user_id="user-123",
            name="John Doe",
            score=0,
            tier=Player.DUMMIES,
            streak=-1,
        )


def test_player_invalid_tier() -> None:
    """Test that invalid tier raises ValueError."""
    with pytest.raises(ValueError, match="tier must be one of"):
        Player(
            user_id="user-123",
            name="John Doe",
            score=0,
            tier="InvalidTier",
            streak=0,
        )


def test_player_is_frozen() -> None:
    """Test that Player is immutable."""
    player = Player(
        user_id="user-123",
        name="John Doe",
        score=0,
        tier=Player.DUMMIES,
        streak=0,
    )

    with pytest.raises(Exception):  # FrozenInstanceError
        player.score = 100  # type: ignore[misc]
