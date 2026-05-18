"""Tests for close prediction window use case."""

import pytest

from src.application.use_cases import ClosePredictionWindowUseCase
from src.domain.entities import Player, Prediction, PredictionWindow, Room
from tests.unit.application.fakes import (
    FakeClock,
    FakeRoomRepository,
    FakeScoreRepository,
    FakeWebSocketBroadcaster,
    FakeWindowRepository,
)


@pytest.fixture
def clock() -> FakeClock:
    """Create fake clock."""
    return FakeClock(initial_ms=1000000)


@pytest.fixture
def window_repo() -> FakeWindowRepository:
    """Create fake window repository."""
    return FakeWindowRepository()


@pytest.fixture
def room_repo() -> FakeRoomRepository:
    """Create fake room repository."""
    return FakeRoomRepository()


@pytest.fixture
def score_repo() -> FakeScoreRepository:
    """Create fake score repository."""
    return FakeScoreRepository()


@pytest.fixture
def broadcaster() -> FakeWebSocketBroadcaster:
    """Create fake broadcaster."""
    return FakeWebSocketBroadcaster()


@pytest.fixture
def use_case(
    window_repo: FakeWindowRepository,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
    clock: FakeClock,
) -> ClosePredictionWindowUseCase:
    """Create close prediction window use case."""
    return ClosePredictionWindowUseCase(
        window_repo=window_repo,
        room_repo=room_repo,
        score_repo=score_repo,
        broadcaster=broadcaster,
        clock=clock,
    )


@pytest.mark.asyncio
async def test_close_window_with_exact_prediction(
    use_case: ClosePredictionWindowUseCase,
    window_repo: FakeWindowRepository,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
    clock: FakeClock,
) -> None:
    """Test closing window with exact prediction awards 100 points."""
    # Setup player
    player = Player(
        player_id="p1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=0,
    )
    await score_repo.upsert_player(player)
    
    # Setup room
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # Setup window
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="CORNERS_IN_INTERVAL",
        prompt="How many corners?",
        correct_answer=3,
        open_at_ms=clock.now_ms(),
        close_at_ms=clock.now_ms() + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    # Player submits exact prediction immediately
    prediction = Prediction(
        player_id="p1",
        value=3,
        submitted_at_ms=clock.now_ms(),
    )
    await window_repo.add_prediction("WIN-1", prediction)
    
    # Close window
    result = await use_case.execute("WIN-1")
    
    # Check result
    assert result.window_id == "WIN-1"
    assert result.correct_answer == 3
    assert result.player_deltas["p1"] == 110  # 100 * 1.1 (instant submission)
    
    # Check player updated
    updated_player = await score_repo.get_player("p1")
    assert updated_player is not None
    assert updated_player.score == 110
    assert updated_player.streak == 1
    
    # Check broadcasts (close, result, leaderboard)
    assert len(broadcaster.broadcast_to_room) == 3


@pytest.mark.asyncio
async def test_close_window_with_ranked_predictions(
    use_case: ClosePredictionWindowUseCase,
    window_repo: FakeWindowRepository,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    clock: FakeClock,
) -> None:
    """Test closing window ranks players by closeness."""
    # Setup players
    players = []
    for i in range(4):
        p = Player(
            player_id=f"p{i+1}",
            name=f"Player{i+1}",
            score=0,
            tier="Dummies",
            streak=0,
        )
        await score_repo.upsert_player(p)
        players.append(p)
    
    room = Room(
        room_id="ROOM-1",
        players=tuple(players),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # Setup window (correct answer = 5)
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="CORNERS_IN_INTERVAL",
        prompt="How many corners?",
        correct_answer=5,
        open_at_ms=clock.now_ms(),
        close_at_ms=clock.now_ms() + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    # Players submit predictions at same time
    await window_repo.add_prediction(
        "WIN-1",
        Prediction(player_id="p1", value=5, submitted_at_ms=clock.now_ms()),  # Exact
    )
    await window_repo.add_prediction(
        "WIN-1",
        Prediction(player_id="p2", value=4, submitted_at_ms=clock.now_ms()),  # Rank 2
    )
    await window_repo.add_prediction(
        "WIN-1",
        Prediction(player_id="p3", value=3, submitted_at_ms=clock.now_ms()),  # Rank 3
    )
    await window_repo.add_prediction(
        "WIN-1",
        Prediction(player_id="p4", value=1, submitted_at_ms=clock.now_ms()),  # Rank 4
    )
    
    result = await use_case.execute("WIN-1")
    
    # Check points (all with 1.1x speed multiplier)
    assert result.player_deltas["p1"] == 110  # 100 * 1.1
    assert result.player_deltas["p2"] == 55   # 50 * 1.1
    assert result.player_deltas["p3"] == 33   # 30 * 1.1
    assert result.player_deltas["p4"] == 22   # 20 * 1.1


@pytest.mark.asyncio
async def test_close_window_with_no_response_penalty(
    use_case: ClosePredictionWindowUseCase,
    window_repo: FakeWindowRepository,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    clock: FakeClock,
) -> None:
    """Test player who doesn't respond gets -10 penalty."""
    # Setup player
    player = Player(
        player_id="p1",
        name="Alice",
        score=100,
        tier="Dummies",
        streak=2,
    )
    await score_repo.upsert_player(player)
    
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # Setup window (no predictions submitted)
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="CORNERS_IN_INTERVAL",
        prompt="How many corners?",
        correct_answer=3,
        open_at_ms=clock.now_ms(),
        close_at_ms=clock.now_ms() + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    result = await use_case.execute("WIN-1")
    
    # Check penalty applied
    assert result.player_deltas["p1"] == -10
    
    # Check player updated
    updated_player = await score_repo.get_player("p1")
    assert updated_player is not None
    assert updated_player.score == 90  # 100 - 10
    assert updated_player.streak == 0  # Reset


@pytest.mark.asyncio
async def test_close_window_with_streak_multiplier(
    use_case: ClosePredictionWindowUseCase,
    window_repo: FakeWindowRepository,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    clock: FakeClock,
) -> None:
    """Test streak multiplier stacks with speed multiplier."""
    # Setup player with 3-streak (1.2x multiplier)
    player = Player(
        player_id="p1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=3,
    )
    await score_repo.upsert_player(player)
    
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # Setup window
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="CORNERS_IN_INTERVAL",
        prompt="How many corners?",
        correct_answer=3,
        open_at_ms=clock.now_ms(),
        close_at_ms=clock.now_ms() + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    # Exact prediction at start
    await window_repo.add_prediction(
        "WIN-1",
        Prediction(player_id="p1", value=3, submitted_at_ms=clock.now_ms()),
    )
    
    result = await use_case.execute("WIN-1")
    
    # Check stacked multipliers: 100 * 1.1 (speed) * 1.2 (streak) = 132
    assert result.player_deltas["p1"] == 132
    
    # Check streak incremented
    updated_player = await score_repo.get_player("p1")
    assert updated_player is not None
    assert updated_player.streak == 4


@pytest.mark.asyncio
async def test_close_window_with_speed_multiplier_decay(
    use_case: ClosePredictionWindowUseCase,
    window_repo: FakeWindowRepository,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    clock: FakeClock,
) -> None:
    """Test speed multiplier decays linearly from 1.1 to 1.0."""
    # Setup player
    player = Player(
        player_id="p1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=0,
    )
    await score_repo.upsert_player(player)
    
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # Setup window
    open_ms = clock.now_ms()
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="CORNERS_IN_INTERVAL",
        prompt="How many corners?",
        correct_answer=3,
        open_at_ms=open_ms,
        close_at_ms=open_ms + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    # Submit at deadline (should get 1.0x multiplier)
    await window_repo.add_prediction(
        "WIN-1",
        Prediction(player_id="p1", value=3, submitted_at_ms=open_ms + 20000),
    )
    
    result = await use_case.execute("WIN-1")
    
    # Check no speed bonus at deadline: 100 * 1.0 = 100
    assert result.player_deltas["p1"] == 100


@pytest.mark.asyncio
async def test_close_window_updates_tier(
    use_case: ClosePredictionWindowUseCase,
    window_repo: FakeWindowRepository,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    clock: FakeClock,
) -> None:
    """Test closing window updates player tier based on new score."""
    # Setup player near tier boundary
    player = Player(
        player_id="p1",
        name="Alice",
        score=390,  # Dummies tier (0-400)
        tier="Dummies",
        streak=0,
    )
    await score_repo.upsert_player(player)
    
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room)
    
    # Setup window
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="CORNERS_IN_INTERVAL",
        prompt="How many corners?",
        correct_answer=3,
        open_at_ms=clock.now_ms(),
        close_at_ms=clock.now_ms() + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    # Exact prediction (will earn 110 points -> 500 total)
    await window_repo.add_prediction(
        "WIN-1",
        Prediction(player_id="p1", value=3, submitted_at_ms=clock.now_ms()),
    )
    
    await use_case.execute("WIN-1")
    
    # Check tier upgraded
    updated_player = await score_repo.get_player("p1")
    assert updated_player is not None
    assert updated_player.score == 500
    assert updated_player.tier == "Enthusiast"  # 401-700


@pytest.mark.asyncio
async def test_close_window_broadcasts_all_messages(
    use_case: ClosePredictionWindowUseCase,
    window_repo: FakeWindowRepository,
    room_repo: FakeRoomRepository,
    score_repo: FakeScoreRepository,
    broadcaster: FakeWebSocketBroadcaster,
    clock: FakeClock,
) -> None:
    """Test closing window broadcasts close, result, and leaderboard."""
    # Setup
    player = Player(
        player_id="p1",
        name="Alice",
        score=0,
        tier="Dummies",
        streak=0,
    )
    await score_repo.upsert_player(player)
    
    room = Room(
        room_id="ROOM-1",
        players=(player,),
        status="active",
        created_at_ms=clock.now_ms(),
    )
    await room_repo.save(room)
    
    window = PredictionWindow(
        window_id="WIN-1",
        room_id="ROOM-1",
        game_type="CORNERS_IN_INTERVAL",
        prompt="How many corners?",
        correct_answer=3,
        open_at_ms=clock.now_ms(),
        close_at_ms=clock.now_ms() + 20000,
        status="open",
    )
    await window_repo.save(window)
    
    await window_repo.add_prediction(
        "WIN-1",
        Prediction(player_id="p1", value=3, submitted_at_ms=clock.now_ms()),
    )
    
    await use_case.execute("WIN-1")
    
    # Check 3 broadcasts
    assert len(broadcaster.broadcast_to_room) == 3
    
    # Check window close message
    close_msg = broadcaster.broadcast_to_room[0]
    assert close_msg["message"]["type"] == "prediction_window_close"
    assert close_msg["message"]["window_id"] == "WIN-1"
    
    # Check result message
    result_msg = broadcaster.broadcast_to_room[1]
    assert result_msg["message"]["type"] == "prediction_result"
    assert result_msg["message"]["correct_answer"] == 3
    assert len(result_msg["message"]["results"]) == 1
    
    # Check leaderboard message
    leaderboard_msg = broadcaster.broadcast_to_room[2]
    assert leaderboard_msg["message"]["type"] == "leaderboard_update"
    assert len(leaderboard_msg["message"]["leaderboard"]) == 1


@pytest.mark.asyncio
async def test_close_nonexistent_window_raises_error(
    use_case: ClosePredictionWindowUseCase,
) -> None:
    """Test closing nonexistent window raises error."""
    with pytest.raises(ValueError, match="Window WIN-999 not found"):
        await use_case.execute("WIN-999")
