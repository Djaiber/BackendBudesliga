"""Unit tests for game_engine_tick scheduled handler."""

from unittest.mock import AsyncMock, patch

from src.domain.entities import Player, Room


def _player(user_id="u1"):
    return Player(user_id=user_id, name="Player", score=0, tier="Dummies", streak=0)


def _room(room_id="r1", player_count=3):
    players = tuple(_player(f"u{i}") for i in range(player_count))
    return Room(room_id=room_id, players=players, status="active", created_at=0)


def _make_container(rooms=None, close_expired=None, open_window=None):
    return {
        "use_cases": {
            "list_active_rooms": AsyncMock(execute=AsyncMock(return_value=rooms or [])),
            "close_expired_windows": AsyncMock(execute=AsyncMock(return_value=close_expired or [])),
            "open_window": AsyncMock(execute=AsyncMock(return_value=None)),
        }
    }


def test_no_active_rooms_returns_200():
    from src.interfaces.event_handlers.game_engine_tick import handler

    container = _make_container(rooms=[])
    with patch("src.interfaces.event_handlers.game_engine_tick.container", container):
        result = handler({}, None)

    assert result["statusCode"] == 200
    container["use_cases"]["open_window"].execute.assert_not_awaited()


def test_active_room_with_expired_window_closes_it():
    from src.interfaces.event_handlers.game_engine_tick import handler

    room = _room()
    container = _make_container(rooms=[room], close_expired=["win1"])
    with patch("src.interfaces.event_handlers.game_engine_tick.container", container):
        result = handler({}, None)

    assert result["statusCode"] == 200
    container["use_cases"]["close_expired_windows"].execute.assert_awaited_once_with(room.room_id)


def test_multiple_rooms_close_expired_called_per_room():
    from src.interfaces.event_handlers.game_engine_tick import handler

    rooms = [_room("r1"), _room("r2"), _room("r3")]
    container = _make_container(rooms=rooms)
    with patch("src.interfaces.event_handlers.game_engine_tick.container", container):
        result = handler({}, None)

    assert result["statusCode"] == 200
    assert container["use_cases"]["close_expired_windows"].execute.await_count == 3


def test_open_window_possibly_called_when_no_expired():
    from src.interfaces.event_handlers.game_engine_tick import handler

    room = _room()
    container = _make_container(rooms=[room], close_expired=[])
    with patch("src.interfaces.event_handlers.game_engine_tick.container", container), \
            patch("src.interfaces.event_handlers.game_engine_tick._should_open_window", return_value=True):
        result = handler({}, None)

    assert result["statusCode"] == 200
    container["use_cases"]["open_window"].execute.assert_awaited_once()
