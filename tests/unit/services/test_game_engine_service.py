"""Tests for GameEngineService."""

from src.domain.entities import MatchEvent, Prediction, PredictionWindow
from src.domain.services.game_engine_service import GameEngineService


def test_game_engine_select_game_no_recent_events() -> None:
    """Test that no recent events selects NEXT_GOAL_TIMING."""
    service = GameEngineService()
    game = service.select_game([], now_ms=1000000)
    assert game == GameEngineService.NEXT_GOAL_TIMING


def test_game_engine_select_game_corners_in_last_3() -> None:
    """Test that corners in last 3 events selects CORNERS_IN_INTERVAL."""
    service = GameEngineService()

    events = [
        MatchEvent("1", 10, 0, "PASS", "team-a", None, None, None, {}),
        MatchEvent("2", 11, 0, "CORNER_KICK", "team-a", None, None, None, {}),
        MatchEvent("3", 12, 0, "PASS", "team-b", None, None, None, {}),
    ]

    game = service.select_game(events, now_ms=1000000)
    assert game == GameEngineService.CORNERS_IN_INTERVAL


def test_game_engine_select_game_shots_no_corners() -> None:
    """Test that shots without corners selects GOAL_IN_TIME_WINDOW."""
    service = GameEngineService()

    events = [
        MatchEvent("1", 10, 0, "PASS", "team-a", None, None, None, {}),
        MatchEvent("2", 11, 0, "SHOT", "team-a", None, None, None, {}),
        MatchEvent("3", 12, 0, "PASS", "team-b", None, None, None, {}),
    ]

    game = service.select_game(events, now_ms=1000000)
    assert game == GameEngineService.GOAL_IN_TIME_WINDOW


def test_game_engine_select_game_determinism() -> None:
    """Test that same inputs produce same output (determinism)."""
    service = GameEngineService()

    events = [
        MatchEvent("1", 10, 0, "PASS", "team-a", None, None, None, {}),
        MatchEvent("2", 11, 0, "SHOT", "team-a", None, None, None, {}),
    ]

    game1 = service.select_game(events, now_ms=1000000)
    game2 = service.select_game(events, now_ms=1000000)

    assert game1 == game2


def test_game_engine_resolve_next_goal_timing() -> None:
    """Test resolving NEXT_GOAL_TIMING with 3 predictions."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.NEXT_GOAL_TIMING,
        prompt="When?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    predictions = [
        Prediction("win-1", "user-1", 45, 1010000),  # Distance 2
        Prediction("win-1", "user-2", 50, 1010000),  # Distance 3
        Prediction("win-1", "user-3", 47, 1010000),  # Distance 0 (exact)
    ]

    events = [
        MatchEvent("1", 47, 30, "GOAL", "team-a", "player-1", None, None, {}),
    ]

    ranks = service.resolve_window(window, predictions, events)

    assert ranks["user-3"] == 1  # Exact
    assert ranks["user-1"] == 2  # Closest
    assert ranks["user-2"] == 3  # Furthest


def test_game_engine_resolve_corners_in_interval() -> None:
    """Test resolving CORNERS_IN_INTERVAL with predictions."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.CORNERS_IN_INTERVAL,
        prompt="How many corners?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    predictions = [
        Prediction("win-1", "user-1", 2, 1010000),  # Distance 1
        Prediction("win-1", "user-2", 3, 1010000),  # Distance 0 (exact)
        Prediction("win-1", "user-3", 5, 1010000),  # Distance 2
    ]

    events = [
        MatchEvent("1", 47, 0, "CORNER_KICK", "team-a", None, None, None, {}),
        MatchEvent("2", 48, 0, "CORNER_KICK", "team-b", None, None, None, {}),
        MatchEvent("3", 49, 0, "CORNER_KICK", "team-a", None, None, None, {}),
    ]

    ranks = service.resolve_window(window, predictions, events)

    assert ranks["user-2"] == 1  # Exact
    assert ranks["user-1"] == 2  # Closest
    assert ranks["user-3"] == 3  # Furthest


def test_game_engine_resolve_goal_in_time_window_yes() -> None:
    """Test resolving GOAL_IN_TIME_WINDOW when goal occurs."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.GOAL_IN_TIME_WINDOW,
        prompt="Will there be a goal?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    predictions = [
        Prediction("win-1", "user-1", "yes", 1010000),
        Prediction("win-1", "user-2", "no", 1010000),
        Prediction("win-1", "user-3", "yes", 1010000),
    ]

    events = [
        MatchEvent("1", 47, 30, "GOAL", "team-a", "player-1", None, None, {}),
    ]

    ranks = service.resolve_window(window, predictions, events)

    assert ranks["user-1"] == 1  # Correct
    assert ranks["user-3"] == 1  # Correct (shared rank)
    assert "user-2" not in ranks  # Wrong


def test_game_engine_resolve_goal_in_time_window_no() -> None:
    """Test resolving GOAL_IN_TIME_WINDOW when no goal occurs."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.GOAL_IN_TIME_WINDOW,
        prompt="Will there be a goal?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    predictions = [
        Prediction("win-1", "user-1", "yes", 1010000),
        Prediction("win-1", "user-2", "no", 1010000),
        Prediction("win-1", "user-3", "no", 1010000),
    ]

    events = [
        MatchEvent("1", 47, 30, "PASS", "team-a", "player-1", None, None, {}),
    ]

    ranks = service.resolve_window(window, predictions, events)

    assert "user-1" not in ranks  # Wrong
    assert ranks["user-2"] == 1  # Correct
    assert ranks["user-3"] == 1  # Correct (shared rank)


def test_game_engine_resolve_no_predictions() -> None:
    """Test resolving with no predictions returns empty dict."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.NEXT_GOAL_TIMING,
        prompt="When?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    events = [
        MatchEvent("1", 47, 30, "GOAL", "team-a", "player-1", None, None, {}),
    ]

    ranks = service.resolve_window(window, [], events)

    assert ranks == {}


def test_game_engine_resolve_next_goal_timing_no_goal() -> None:
    """Test resolving NEXT_GOAL_TIMING when no goal occurs."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.NEXT_GOAL_TIMING,
        prompt="When?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    predictions = [
        Prediction("win-1", "user-1", 45, 1010000),
    ]

    events = [
        MatchEvent("1", 47, 30, "PASS", "team-a", "player-1", None, None, {}),
    ]

    ranks = service.resolve_window(window, predictions, events)

    assert ranks == {}  # No goal, no winners


def test_game_engine_resolve_handles_ties() -> None:
    """Test that exact matches across multiple users all share rank 1."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.NEXT_GOAL_TIMING,
        prompt="When?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    predictions = [
        Prediction("win-1", "user-1", 47, 1010000),
        Prediction("win-1", "user-2", 47, 1010000),
        Prediction("win-1", "user-3", 50, 1010000),
    ]

    events = [
        MatchEvent("1", 47, 30, "GOAL", "team-a", "player-1", None, None, {}),
    ]

    ranks = service.resolve_window(window, predictions, events)

    assert ranks["user-1"] == 1
    assert ranks["user-2"] == 1
    assert ranks["user-3"] == 3  # After two rank-1 players


def test_game_engine_select_game_only_checks_last_3() -> None:
    """Test that only last 3 events are checked for game selection."""
    service = GameEngineService()

    # Corner in 4th-to-last position (should be ignored)
    events = [
        MatchEvent("1", 10, 0, "CORNER_KICK", "team-a", None, None, None, {}),
        MatchEvent("2", 11, 0, "PASS", "team-a", None, None, None, {}),
        MatchEvent("3", 12, 0, "PASS", "team-b", None, None, None, {}),
        MatchEvent("4", 13, 0, "PASS", "team-a", None, None, None, {}),
    ]

    game = service.select_game(events, now_ms=1000000)
    assert game == GameEngineService.NEXT_GOAL_TIMING  # No corner in last 3


def test_game_engine_resolve_invalid_prediction_values() -> None:
    """Test that invalid prediction values are skipped."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.NEXT_GOAL_TIMING,
        prompt="When?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    predictions = [
        Prediction("win-1", "user-1", "invalid", 1010000),  # Invalid int
        Prediction("win-1", "user-2", 47, 1010000),  # Valid
    ]

    events = [
        MatchEvent("1", 47, 30, "GOAL", "team-a", "player-1", None, None, {}),
    ]

    ranks = service.resolve_window(window, predictions, events)

    assert "user-1" not in ranks  # Invalid prediction skipped
    assert ranks["user-2"] == 1  # Valid prediction ranked


def test_game_engine_resolve_corners_invalid_values() -> None:
    """Test CORNERS_IN_INTERVAL with invalid prediction values."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.CORNERS_IN_INTERVAL,
        prompt="How many?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    predictions = [
        Prediction("win-1", "user-1", "not-a-number", 1010000),  # Invalid
        Prediction("win-1", "user-2", 3, 1010000),  # Valid
    ]

    events = [
        MatchEvent("1", 47, 0, "CORNER_KICK", "team-a", None, None, None, {}),
        MatchEvent("2", 48, 0, "CORNER_KICK", "team-b", None, None, None, {}),
        MatchEvent("3", 49, 0, "CORNER_KICK", "team-a", None, None, None, {}),
    ]

    ranks = service.resolve_window(window, predictions, events)

    assert "user-1" not in ranks
    assert ranks["user-2"] == 1


def test_game_engine_resolve_goal_window_false_prediction() -> None:
    """Test GOAL_IN_TIME_WINDOW with 'false' string prediction."""
    service = GameEngineService()

    window = PredictionWindow(
        window_id="win-1",
        room_id="room-1",
        game=GameEngineService.GOAL_IN_TIME_WINDOW,
        prompt="Will there be a goal?",
        opened_at_ms=1000000,
        deadline_ms=1020000,
        options=None,
        status=PredictionWindow.OPEN,
    )

    predictions = [
        Prediction("win-1", "user-1", "false", 1010000),  # No prediction
        Prediction("win-1", "user-2", "0", 1010000),  # No prediction
    ]

    events = []  # No goal

    ranks = service.resolve_window(window, predictions, events)

    assert ranks["user-1"] == 1  # Correct
    assert ranks["user-2"] == 1  # Correct
