"""Tests for ScoringService."""


from src.domain.services.scoring_service import ScoringService


def test_scoring_service_exact_at_deadline() -> None:
    """Test exact prediction submitted at deadline."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=True,
        rank=1,
        submitted_at_ms=1020000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 100
    assert speed == 1.0


def test_scoring_service_exact_at_open() -> None:
    """Test exact prediction submitted at open time."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=True,
        rank=1,
        submitted_at_ms=1000000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 100
    assert abs(speed - 1.1) < 0.001  # Float tolerance


def test_scoring_service_exact_mid_window() -> None:
    """Test exact prediction submitted mid-window."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=True,
        rank=1,
        submitted_at_ms=1010000,  # Halfway
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 100
    assert abs(speed - 1.05) < 0.001  # Halfway between 1.1 and 1.0


def test_scoring_service_rank_2() -> None:
    """Test rank 2 gets 50 points."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=False,
        rank=2,
        submitted_at_ms=1020000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 50
    assert speed == 1.0


def test_scoring_service_rank_3() -> None:
    """Test rank 3 gets 30 points."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=False,
        rank=3,
        submitted_at_ms=1020000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 30


def test_scoring_service_rank_4() -> None:
    """Test rank 4 gets 20 points."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=False,
        rank=4,
        submitted_at_ms=1020000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 20


def test_scoring_service_rank_5() -> None:
    """Test rank 5 gets 10 points."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=False,
        rank=5,
        submitted_at_ms=1020000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 10


def test_scoring_service_rank_6() -> None:
    """Test rank 6+ gets 0 points."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=False,
        rank=6,
        submitted_at_ms=1020000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 0


def test_scoring_service_no_response() -> None:
    """Test no response gets -10 penalty."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=False,
        rank=None,
        submitted_at_ms=1020000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == -10
    assert speed == 1.0  # Speed multiplier not applied to penalties


def test_scoring_service_apply_streak_positive() -> None:
    """Test applying streak multiplier to positive points."""
    service = ScoringService()
    final = service.apply_streak(
        base_points=100,
        speed_multiplier=1.1,
        streak_multiplier=1.2,
    )

    # 100 * 1.1 * 1.2 = 132
    assert final == 132


def test_scoring_service_apply_streak_negative() -> None:
    """Test that multipliers are NOT applied to negative points."""
    service = ScoringService()
    final = service.apply_streak(
        base_points=-10,
        speed_multiplier=1.1,
        streak_multiplier=1.2,
    )

    assert final == -10  # Unchanged


def test_scoring_service_apply_streak_rounding() -> None:
    """Test that final result is rounded to integer."""
    service = ScoringService()
    final = service.apply_streak(
        base_points=100,
        speed_multiplier=1.05,
        streak_multiplier=1.2,
    )

    # 100 * 1.05 * 1.2 = 126.0
    assert final == 126
    assert isinstance(final, int)


def test_scoring_service_speed_multiplier_before_open() -> None:
    """Test speed multiplier when submitted before open (edge case)."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=True,
        rank=1,
        submitted_at_ms=999999,  # Before open
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 100
    assert abs(speed - 1.1) < 0.001  # Max multiplier


def test_scoring_service_speed_multiplier_after_deadline() -> None:
    """Test speed multiplier when submitted after deadline (edge case)."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=True,
        rank=1,
        submitted_at_ms=1030000,  # After deadline
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 100
    assert speed == 1.0  # Min multiplier


def test_scoring_service_rank_0_gets_zero() -> None:
    """Test rank 0 gets 0 points."""
    service = ScoringService()
    base, speed = service.score_submission(
        is_exact=False,
        rank=0,
        submitted_at_ms=1020000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=0,
    )

    assert base == 0


def test_scoring_service_full_multiplier_stack() -> None:
    """Test that speed and streak multipliers stack correctly."""
    service = ScoringService()

    # Get base and speed for exact prediction at open
    base, speed = service.score_submission(
        is_exact=True,
        rank=1,
        submitted_at_ms=1000000,
        opened_at_ms=1000000,
        deadline_ms=1020000,
        current_streak=5,
    )

    # Apply streak multiplier
    final = service.apply_streak(base, speed, 1.5)

    # 100 * 1.1 * 1.5 = 165
    assert final == 165
