"""Tests for Prediction entity."""

import pytest

from src.domain.entities import Prediction


def test_prediction_happy_path_string_value() -> None:
    """Test creating a valid prediction with string value."""
    prediction = Prediction(
        window_id="win-123",
        user_id="user-456",
        value="yes",
        submitted_at_ms=1010000,
    )

    assert prediction.window_id == "win-123"
    assert prediction.user_id == "user-456"
    assert prediction.value == "yes"
    assert prediction.submitted_at_ms == 1010000


def test_prediction_happy_path_int_value() -> None:
    """Test creating a valid prediction with integer value."""
    prediction = Prediction(
        window_id="win-123",
        user_id="user-456",
        value=47,
        submitted_at_ms=1010000,
    )

    assert prediction.value == 47


def test_prediction_is_frozen() -> None:
    """Test that Prediction is immutable."""
    prediction = Prediction(
        window_id="win-123",
        user_id="user-456",
        value="yes",
        submitted_at_ms=1010000,
    )

    with pytest.raises(Exception):  # FrozenInstanceError
        prediction.value = "no"  # type: ignore[misc]
