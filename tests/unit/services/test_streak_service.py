"""Tests for StreakService."""

from src.domain.services.streak_service import StreakService


def test_streak_service_next_streak_correct_increments() -> None:
    """Test that correct prediction increments streak."""
    service = StreakService()
    assert service.next_streak(0, correct=True) == 1
    assert service.next_streak(1, correct=True) == 2
    assert service.next_streak(5, correct=True) == 6


def test_streak_service_next_streak_wrong_resets() -> None:
    """Test that wrong prediction resets streak to 0."""
    service = StreakService()
    assert service.next_streak(0, correct=False) == 0
    assert service.next_streak(1, correct=False) == 0
    assert service.next_streak(10, correct=False) == 0


def test_streak_service_multiplier_0() -> None:
    """Test multiplier for streak 0."""
    service = StreakService()
    assert service.multiplier_for(0) == 1.0


def test_streak_service_multiplier_1() -> None:
    """Test multiplier for streak 1."""
    service = StreakService()
    assert service.multiplier_for(1) == 1.0


def test_streak_service_multiplier_2() -> None:
    """Test multiplier for streak 2."""
    service = StreakService()
    assert service.multiplier_for(2) == 1.0


def test_streak_service_multiplier_3() -> None:
    """Test multiplier for streak 3 (threshold)."""
    service = StreakService()
    assert service.multiplier_for(3) == 1.2


def test_streak_service_multiplier_4() -> None:
    """Test multiplier for streak 4."""
    service = StreakService()
    assert service.multiplier_for(4) == 1.2


def test_streak_service_multiplier_5() -> None:
    """Test multiplier for streak 5 (threshold)."""
    service = StreakService()
    assert service.multiplier_for(5) == 1.5


def test_streak_service_multiplier_6() -> None:
    """Test multiplier for streak 6."""
    service = StreakService()
    assert service.multiplier_for(6) == 1.5


def test_streak_service_multiplier_100() -> None:
    """Test multiplier for very high streak."""
    service = StreakService()
    assert service.multiplier_for(100) == 1.5
