"""Tests for submit prediction use case."""

import pytest

from src.application.use_cases import SubmitPredictionUseCase
from src.domain.entities import PredictionWindow
from tests.unit.application.fakes import FakeClock, FakeWindowRepository


@pytest.fixture
def clock() -> FakeClock:
    """Create fake clock."""
    return FakeClock(initial_ms=1000000)


@pytest.fixture
def window_repo() -> FakeWindowRepository:
    """Create fake window repository."""
    return FakeWindowRepository()


@pytest.fixture
def use_case(
    window_repo: FakeWindowRepository,
    clock: FakeClock,
) -> SubmitPredictionUseCase:
    """Create submit prediction use case."""
    return SubmitPredictionUseCase(
        window_repo=window_repo,
        clock=clock,
    )


@pytest.mark.asyncio
async def test_submit_prediction_success(
    use_case: SubmitPredictionUseCase,
    window_repo: FakeWindowRepository,
    clock: FakeClock,
) -> None:
    """Test successful prediction submission."""
    # Create open window
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="NEXT_GOAL_TIMING",
        prompt="When will the next goal be scored?",
        correct_answer="15:30",
        open_at_ms=clock.now_ms(),
        close_at_ms=clock.now_ms() + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    # Submit prediction
    result = await use_case.execute(
        window_id="WIN-1",
        player_id="p1",
        value="16:00",
    )
    
    assert result.success is True
    assert result.error is None
    
    # Check prediction stored
    predictions = await window_repo.list_predictions("WIN-1")
    assert len(predictions) == 1
    assert predictions[0].player_id == "p1"
    assert predictions[0].value == "16:00"
    assert predictions[0].submitted_at_ms == clock.now_ms()


@pytest.mark.asyncio
async def test_submit_to_nonexistent_window(
    use_case: SubmitPredictionUseCase,
) -> None:
    """Test submitting to nonexistent window fails."""
    result = await use_case.execute(
        window_id="WIN-999",
        player_id="p1",
        value="10:00",
    )
    
    assert result.success is False
    assert "not found" in result.error  # type: ignore


@pytest.mark.asyncio
async def test_submit_to_closed_window(
    use_case: SubmitPredictionUseCase,
    window_repo: FakeWindowRepository,
    clock: FakeClock,
) -> None:
    """Test submitting to closed window fails."""
    # Create closed window
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="NEXT_GOAL_TIMING",
        prompt="When will the next goal be scored?",
        correct_answer="15:30",
        open_at_ms=clock.now_ms() - 30000,
        close_at_ms=clock.now_ms() - 10000,
        status="closed",
        closed_at_ms=clock.now_ms() - 10000,
    )
    await window_repo.save(window)
    
    result = await use_case.execute(
        window_id="WIN-1",
        player_id="p1",
        value="16:00",
    )
    
    assert result.success is False
    assert "not open" in result.error  # type: ignore


@pytest.mark.asyncio
async def test_submit_to_expired_window(
    use_case: SubmitPredictionUseCase,
    window_repo: FakeWindowRepository,
    clock: FakeClock,
) -> None:
    """Test submitting to expired window fails."""
    # Create window that's open but expired
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="NEXT_GOAL_TIMING",
        prompt="When will the next goal be scored?",
        correct_answer="15:30",
        open_at_ms=clock.now_ms() - 30000,
        close_at_ms=clock.now_ms() - 1000,  # Expired
        status="open",
    )
    await window_repo.save(window)
    
    result = await use_case.execute(
        window_id="WIN-1",
        player_id="p1",
        value="16:00",
    )
    
    assert result.success is False
    assert "expired" in result.error  # type: ignore


@pytest.mark.asyncio
async def test_duplicate_prediction_rejected(
    use_case: SubmitPredictionUseCase,
    window_repo: FakeWindowRepository,
    clock: FakeClock,
) -> None:
    """Test player cannot submit multiple predictions to same window."""
    # Create open window
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="NEXT_GOAL_TIMING",
        prompt="When will the next goal be scored?",
        correct_answer="15:30",
        open_at_ms=clock.now_ms(),
        close_at_ms=clock.now_ms() + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    # First submission succeeds
    result1 = await use_case.execute(
        window_id="WIN-1",
        player_id="p1",
        value="16:00",
    )
    assert result1.success is True
    
    # Second submission fails
    result2 = await use_case.execute(
        window_id="WIN-1",
        player_id="p1",
        value="17:00",
    )
    assert result2.success is False
    assert "already submitted" in result2.error  # type: ignore
    
    # Only one prediction stored
    predictions = await window_repo.list_predictions("WIN-1")
    assert len(predictions) == 1


@pytest.mark.asyncio
async def test_multiple_players_can_submit(
    use_case: SubmitPredictionUseCase,
    window_repo: FakeWindowRepository,
    clock: FakeClock,
) -> None:
    """Test multiple players can submit to same window."""
    # Create open window
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="CORNERS_IN_INTERVAL",
        prompt="How many corners in next 5 minutes?",
        correct_answer=3,
        open_at_ms=clock.now_ms(),
        close_at_ms=clock.now_ms() + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    # Multiple players submit
    result1 = await use_case.execute(window_id="WIN-1", player_id="p1", value=2)
    result2 = await use_case.execute(window_id="WIN-1", player_id="p2", value=3)
    result3 = await use_case.execute(window_id="WIN-1", player_id="p3", value=4)
    
    assert result1.success is True
    assert result2.success is True
    assert result3.success is True
    
    # All predictions stored
    predictions = await window_repo.list_predictions("WIN-1")
    assert len(predictions) == 3
