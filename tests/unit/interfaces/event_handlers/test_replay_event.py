"""Unit tests for EventBridge MatchEvent consumer handler."""

from unittest.mock import AsyncMock, patch


def _make_event(detail=None):
    return {"detail": detail or _valid_detail()}


def _valid_detail(**overrides):
    d = {
        "event_id": "evt1",
        "minute": 12,
        "second": 34,
        "event_type": "GOAL",
        "team": "Home",
        "player": "Müller",
        "x_position": 50.0,
        "y_position": 25.0,
        "metadata": {},
    }
    d.update(overrides)
    return d


def _make_container(handle_match_event=None):
    return {"use_cases": {"handle_match_event": handle_match_event or AsyncMock()}}


def test_valid_event_calls_handle_match_event_and_returns_200():
    from src.interfaces.event_handlers.replay_event import handler

    handle = AsyncMock()
    container = _make_container(handle_match_event=handle)
    with patch("src.interfaces.event_handlers.replay_event.container", container):
        result = handler(_make_event(), None)

    assert result["statusCode"] == 200
    handle.execute.assert_awaited_once()
    match_event = handle.execute.call_args.args[0]
    assert match_event.event_id == "evt1"
    assert match_event.minute == 12
    assert match_event.event_type == "GOAL"


def test_event_with_optional_fields_absent_succeeds():
    from src.interfaces.event_handlers.replay_event import handler

    detail = _valid_detail()
    del detail["player"]
    del detail["x_position"]
    del detail["y_position"]
    del detail["metadata"]

    container = _make_container()
    with patch("src.interfaces.event_handlers.replay_event.container", container):
        result = handler(_make_event(detail), None)

    assert result["statusCode"] == 200


def test_missing_required_field_returns_400():
    from src.interfaces.event_handlers.replay_event import handler

    detail = _valid_detail()
    del detail["event_type"]

    container = _make_container()
    with patch("src.interfaces.event_handlers.replay_event.container", container):
        result = handler(_make_event(detail), None)

    assert result["statusCode"] == 400


def test_invalid_event_type_returns_400():
    from src.interfaces.event_handlers.replay_event import handler

    container = _make_container()
    with patch("src.interfaces.event_handlers.replay_event.container", container):
        result = handler(_make_event(_valid_detail(event_type="ROCKET_LAUNCH")), None)

    assert result["statusCode"] == 400


def test_invalid_minute_returns_400():
    from src.interfaces.event_handlers.replay_event import handler

    container = _make_container()
    with patch("src.interfaces.event_handlers.replay_event.container", container):
        result = handler(_make_event(_valid_detail(minute=999)), None)

    assert result["statusCode"] == 400
