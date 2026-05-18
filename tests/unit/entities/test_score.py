"""Tests for ScoreDelta entity."""

import pytest

from src.domain.entities import Player, ScoreDelta


def test_score_delta_happy_path() -> None:
    """Test creating a valid score delta."""
    delta = ScoreDelta(
        user_id="user-123",
        points=100,
        new_score=600,
        new_streak=4,
        new_tier=Player.ENTHUSIAST,
        multiplier_applied=1.2,
    )

    assert delta.user_id == "user-123"
    assert delta.points == 100
    assert delta.new_score == 600
    assert delta.new_streak == 4
    assert delta.multiplier_applied == 1.2


def test_score_delta_negative_points() -> None:
    """Test creating a score delta with negative points (penalty)."""
    delta = ScoreDelta(
        user_id="user-123",
        points=-10,
        new_score=90,
        new_streak=0,
        new_tier=Player.DUMMIES,
        multiplier_applied=1.0,
    )

    assert delta.points == -10


def test_score_delta_is_frozen() -> None:
    """Test that ScoreDelta is immutable."""
    delta = ScoreDelta(
        user_id="user-123",
        points=100,
        new_score=600,
        new_streak=4,
        new_tier=Player.ENTHUSIAST,
        multiplier_applied=1.2,
    )

    with pytest.raises(Exception):  # FrozenInstanceError
        delta.points = 200  # type: ignore[misc]
