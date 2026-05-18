"""Tests for open prediction window use case."""

import pytest

from src.application.use_cases import OpenPredictionWindowUseCase
from src.domain.entities import MatchEvent
from tests.unit.application.fakes import (
    FakeAIGenerator,
    FakeClock,
    FakeIdGenerator,
    FakeWebSocketBroadcaster,
    FakeWindowRepository,
)


@pytest.fixture
def clock() -> FakeClock:
    """Create fake clock."""
    return FakeClock(initial_ms=1000000)


@pytest.fixture
def id_gen() -> FakeIdGenerator:
    """Create fake ID generator."""
    return FakeIdGenerator()


@pytest.fixture
def window_repo() -> FakeWindowRepository:
    """Create fake window repository."""
    return FakeWindowRepository()


@pytest.fixture
def broadcaster() -> FakeWebSocketBroadcaster:
    """Create fake broadcaster."""
    return FakeWebSocketBroadcaster()


@pytest.fixture
def ai_gen() -> FakeAIGenerator:
    """Create fake AI generator."""
    return FakeAIGenerator(default_prompt="Test prompt")


@pytest.fixture
def use_case(
    window_repo: FakeWindowRepository,
    broadcaster: FakeWebSocketBroadcaster,
    ai_gen: FakeAIGenerator,
    id_gen: FakeIdGenerator,
    clock: FakeClock,
) -> OpenPredictionWindowUseCase:
    """Create open prediction window use case."""
    return OpenPredictionWindowUseCase(
        window_repo=window_repo,
        broadcaster=broadcaster,
        ai_gen=ai_gen,
        id_gen=id_gen,
        clock=clock,
    )


@pytest.mark.asyncio
async def test_open_window_with_corners_game(
    use_case: OpenPredictionWindowUseCase,
    window_repo: FakeWindowRepository,
    broadcaster: FakeWebSocketBroadcaster,
    ai_gen: FakeAIGenerator,
    clock: FakeClock,
) -> None:
    """Test opening window selects CORNERS_IN_INTERVAL for recent corners."""
    # Recent corner events
    events = [
        MatchEvent(event_type="corner", minute=10, second=0, team="home"),
        MatchEvent(event_type="corner", minute=10, second=30, team="away"),
    ]
    
    window = await use_case.execute(
        room_id="ROOM-1",
        recent_events=events,
        correct_answer=3,
    )
    
    # Check window created
    assert window.window_id == "WIN-1"
    assert window.room_id == "ROOM-1"
    assert window.game_type == "CORNERS_IN_INTERVAL"
    assert window.prompt == "Test prompt"
    assert window.correct_answer == 3
    assert window.open_at_ms == clock.now_ms()
    assert window.close_at_ms == clock.now_ms() + 20000
    assert window.status == "open"
    
    # Check window saved
    saved = await window_repo.get("WIN-1")
    assert saved is not None
    assert saved.game_type == "CORNERS_IN_INTERVAL"
    
    # Check AI generator called
    assert len(ai_gen.calls) == 1
    assert ai_gen.calls[0]["game_type"] == "CORNERS_IN_INTERVAL"
    
    # Check broadcast
    assert len(broadcaster.broadcast_to_room) == 1
    msg = broadcaster.broadcast_to_room[0]
    assert msg["room_id"] == "ROOM-1"
    assert msg["message"]["type"] == "prediction_window_open"
    assert msg["message"]["window_id"] == "WIN-1"
    assert msg["message"]["game_type"] == "CORNERS_IN_INTERVAL"


@pytest.mark.asyncio
async def test_open_window_with_goal_timing_game(
    use_case: OpenPredictionWindowUseCase,
    window_repo: FakeWindowRepository,
) -> None:
    """Test opening window selects GOAL_IN_TIME_WINDOW for recent shots."""
    # Recent shot events (no corners)
    events = [
        MatchEvent(event_type="shot", minute=15, second=0, team="home"),
        MatchEvent(event_type="shot", minute=15, second=20, team="away"),
    ]
    
    window = await use_case.execute(
        room_id="ROOM-1",
        recent_events=events,
        correct_answer="16:30",
    )
    
    assert window.game_type == "GOAL_IN_TIME_WINDOW"
    assert window.correct_answer == "16:30"


@pytest.mark.asyncio
async def test_open_window_with_next_goal_timing(
    use_case: OpenPredictionWindowUseCase,
    window_repo: FakeWindowRepository,
) -> None:
    """Test opening window selects NEXT_GOAL_TIMING for no recent events."""
    # No recent events
    events: list[MatchEvent] = []
    
    window = await use_case.execute(
        room_id="ROOM-1",
        recent_events=events,
        correct_answer="20:00",
    )
    
    assert window.game_type == "NEXT_GOAL_TIMING"
    assert window.correct_answer == "20:00"


@pytest.mark.asyncio
async def test_window_duration_is_20_seconds(
    use_case: OpenPredictionWindowUseCase,
    clock: FakeClock,
) -> None:
    """Test window duration is exactly 20 seconds."""
    window = await use_case.execute(
        room_id="ROOM-1",
        recent_events=[],
        correct_answer="10:00",
    )
    
    duration = window.close_at_ms - window.open_at_ms
    assert duration == 20000  # 20 seconds in milliseconds


@pytest.mark.asyncio
async def test_sequential_windows_get_unique_ids(
    use_case: OpenPredictionWindowUseCase,
) -> None:
    """Test multiple windows get unique IDs."""
    window1 = await use_case.execute(
        room_id="ROOM-1",
        recent_events=[],
        correct_answer="10:00",
    )
    
    window2 = await use_case.execute(
        room_id="ROOM-1",
        recent_events=[],
        correct_answer="11:00",
    )
    
    assert window1.window_id == "WIN-1"
    assert window2.window_id == "WIN-2"
    assert window1.window_id != window2.window_id


@pytest.mark.asyncio
async def test_ai_generator_receives_context(
    use_case: OpenPredictionWindowUseCase,
    ai_gen: FakeAIGenerator,
) -> None:
    """Test AI generator receives event context."""
    events = [
        MatchEvent(
            event_type="corner",
            minute=10,
            second=30,
            team="home",
            player_name="Alice",
        ),
    ]
    
    await use_case.execute(
        room_id="ROOM-1",
        recent_events=events,
        correct_answer=2,
    )
    
    # Check context passed to AI
    assert len(ai_gen.calls) == 1
    context = ai_gen.calls[0]["context"]
    assert "recent_events" in context
    assert len(context["recent_events"]) == 1
    assert context["recent_events"][0]["event_type"] == "corner"
    assert context["recent_events"][0]["minute"] == 10
