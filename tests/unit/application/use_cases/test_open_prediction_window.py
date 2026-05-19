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
    return FakeClock(initial_ms=1000000)


@pytest.fixture
def id_gen() -> FakeIdGenerator:
    return FakeIdGenerator()


@pytest.fixture
def window_repo() -> FakeWindowRepository:
    return FakeWindowRepository()


@pytest.fixture
def broadcaster() -> FakeWebSocketBroadcaster:
    return FakeWebSocketBroadcaster()


@pytest.fixture
def ai_gen() -> FakeAIGenerator:
    return FakeAIGenerator(default_prompt="Test prompt")


@pytest.fixture
def use_case(
    window_repo: FakeWindowRepository,
    broadcaster: FakeWebSocketBroadcaster,
    ai_gen: FakeAIGenerator,
    id_gen: FakeIdGenerator,
    clock: FakeClock,
) -> OpenPredictionWindowUseCase:
    return OpenPredictionWindowUseCase(
        window_repo=window_repo,
        broadcaster=broadcaster,
        ai_gen=ai_gen,
        id_gen=id_gen,
        clock=clock,
    )


def make_event(
    event_type: str, minute: int, second: int = 0, team: str = "home", player: str | None = None
) -> MatchEvent:
    """Helper to build a MatchEvent with all required fields."""
    return MatchEvent(
        event_id=f"{event_type}-{minute}-{second}",
        minute=minute,
        second=second,
        event_type=event_type,
        team=team,
        player=player,
        x_position=None,
        y_position=None,
        metadata={},
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
    events = [
        make_event("CORNER_KICK", 10, 0, "home"),
        make_event("CORNER_KICK", 10, 30, "away"),
    ]

    window = await use_case.execute(
        room_id="ROOM-1",
        recent_events=events,
        correct_answer=3,
    )

    assert window.window_id == "WIN-1"
    assert window.room_id == "ROOM-1"
    assert window.game == "CORNERS_IN_INTERVAL"
    assert window.prompt == "Test prompt"
    assert window.opened_at_ms == clock.now_ms()
    assert window.deadline_ms == clock.now_ms() + 20000
    assert window.status == "open"

    saved = await window_repo.get("WIN-1")
    assert saved is not None
    assert saved.game == "CORNERS_IN_INTERVAL"

    assert len(ai_gen.calls) == 1
    assert ai_gen.calls[0]["game"] == "CORNERS_IN_INTERVAL"

    assert len(broadcaster.broadcast_to_room_calls) == 1
    msg = broadcaster.broadcast_to_room_calls[0]
    assert msg["room_id"] == "ROOM-1"
    assert msg["message"]["type"] == "prediction_window_open"
    assert msg["message"]["window_id"] == "WIN-1"
    assert msg["message"]["game"] == "CORNERS_IN_INTERVAL"


@pytest.mark.asyncio
async def test_open_window_with_goal_timing_game(
    use_case: OpenPredictionWindowUseCase,
) -> None:
    """Test opening window selects GOAL_IN_TIME_WINDOW for recent shots."""
    events = [
        make_event("SHOT", 15, 0, "home"),
        make_event("SHOT", 15, 20, "away"),
    ]

    window = await use_case.execute(
        room_id="ROOM-1",
        recent_events=events,
        correct_answer="16:30",
    )

    assert window.game == "GOAL_IN_TIME_WINDOW"


@pytest.mark.asyncio
async def test_open_window_with_next_goal_timing(
    use_case: OpenPredictionWindowUseCase,
) -> None:
    """Test opening window selects NEXT_GOAL_TIMING for no recent events."""
    window = await use_case.execute(
        room_id="ROOM-1",
        recent_events=[],
        correct_answer="20:00",
    )

    assert window.game == "NEXT_GOAL_TIMING"


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

    duration = window.deadline_ms - window.opened_at_ms
    assert duration == 20000


@pytest.mark.asyncio
async def test_sequential_windows_get_unique_ids(
    use_case: OpenPredictionWindowUseCase,
) -> None:
    """Test multiple windows get unique IDs."""
    window1 = await use_case.execute(room_id="ROOM-1", recent_events=[], correct_answer="10:00")
    window2 = await use_case.execute(room_id="ROOM-1", recent_events=[], correct_answer="11:00")

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
        make_event("CORNER_KICK", 10, 30, "home", "Alice"),
    ]

    await use_case.execute(room_id="ROOM-1", recent_events=events, correct_answer=2)

    assert len(ai_gen.calls) == 1
    recent_events = ai_gen.calls[0]["recent_events"]
    assert len(recent_events) == 1
    assert recent_events[0].event_type == "CORNER_KICK"
    assert recent_events[0].minute == 10
