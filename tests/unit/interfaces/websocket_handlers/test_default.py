"""Unit tests for $default message router handler."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.application.dto.results import SubmitPredictionResult
from src.domain.entities import Player, Room


def _make_event(body=None, connection_id="conn1"):
    return {
        "requestContext": {"connectionId": connection_id},
        "body": json.dumps(body) if body else None,
    }


def _conn(room_id="room1", user_id="u1", user_name="Alice"):
    return {"user_id": user_id, "user_name": user_name, "room_id": room_id}


def _player():
    return Player(user_id="u1", name="Alice", score=0, tier="Dummies", streak=0)


def _room():
    return Room(room_id="room1", players=(_player(),), status="active", created_at=0)


def _make_container(connections=None, broadcaster=None, use_cases=None):
    return {
        "connections": connections or AsyncMock(get=AsyncMock(return_value=_conn())),
        "broadcaster": broadcaster or AsyncMock(),
        "use_cases": use_cases or {},
    }


# ── PING ──────────────────────────────────────────────────────────────────────

def test_ping_sends_pong_and_returns_200():
    from src.interfaces.websocket_handlers.default import handler

    broadcaster = AsyncMock()
    container = _make_container(broadcaster=broadcaster)
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"type": "PING"}), None)

    assert result["statusCode"] == 200
    broadcaster.send_to_connection.assert_awaited_once_with("conn1", {"type": "PONG"})


# ── JOIN_ROOM ─────────────────────────────────────────────────────────────────

def test_join_room_calls_use_case_and_returns_200():
    from src.interfaces.websocket_handlers.default import handler

    join_room = AsyncMock()
    join_room.execute.return_value = MagicMock(room=_room())
    connections = AsyncMock(
        get=AsyncMock(return_value=_conn(room_id="")),
        update_room=AsyncMock(),
    )
    container = _make_container(
        connections=connections,
        use_cases={"join_room": join_room},
    )
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"type": "JOIN_ROOM"}), None)

    assert result["statusCode"] == 200
    join_room.execute.assert_awaited_once()
    connections.update_room.assert_awaited_once_with("conn1", "room1")


# ── SUBMIT_PREDICTION ─────────────────────────────────────────────────────────

def test_submit_prediction_accepted_returns_200():
    from src.interfaces.websocket_handlers.default import handler

    submit = AsyncMock(execute=AsyncMock(return_value=SubmitPredictionResult(success=True)))
    container = _make_container(use_cases={"submit_prediction": submit})
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"type": "SUBMIT_PREDICTION", "windowId": "win1", "value": 2}), None)

    assert result["statusCode"] == 200
    submit.execute.assert_awaited_once_with(window_id="win1", user_id="u1", value=2)


def test_submit_prediction_rejected_returns_400():
    from src.interfaces.websocket_handlers.default import handler

    submit = AsyncMock(
        execute=AsyncMock(return_value=SubmitPredictionResult(success=False, error="Window closed"))
    )
    container = _make_container(use_cases={"submit_prediction": submit})
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"type": "SUBMIT_PREDICTION", "windowId": "win1", "value": 1}), None)

    assert result["statusCode"] == 400
    assert "Window closed" in result["body"]


def test_submit_prediction_missing_window_id_returns_400():
    from src.interfaces.websocket_handlers.default import handler

    container = _make_container(use_cases={"submit_prediction": AsyncMock()})
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"type": "SUBMIT_PREDICTION", "value": 1}), None)

    assert result["statusCode"] == 400


# ── EMOJI ─────────────────────────────────────────────────────────────────────

def test_emoji_valid_calls_use_case_returns_200():
    from src.interfaces.websocket_handlers.default import handler

    broadcast_emoji = AsyncMock()
    container = _make_container(use_cases={"broadcast_emoji": broadcast_emoji})
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"type": "EMOJI", "emoji": "🔥"}), None)

    assert result["statusCode"] == 200
    broadcast_emoji.execute.assert_awaited_once_with(room_id="room1", user_id="u1", emoji="🔥")


def test_emoji_without_room_returns_400():
    from src.interfaces.websocket_handlers.default import handler

    connections = AsyncMock(get=AsyncMock(return_value=_conn(room_id="")))
    container = _make_container(connections=connections, use_cases={"broadcast_emoji": AsyncMock()})
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"type": "EMOJI", "emoji": "🔥"}), None)

    assert result["statusCode"] == 400


# ── EDGE CASES ────────────────────────────────────────────────────────────────

def test_malformed_json_returns_400():
    from src.interfaces.websocket_handlers.default import handler

    container = _make_container()
    event = {"requestContext": {"connectionId": "conn1"}, "body": "{bad json"}
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(event, None)

    assert result["statusCode"] == 400


def test_missing_type_field_returns_400():
    from src.interfaces.websocket_handlers.default import handler

    container = _make_container()
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"data": "hello"}), None)

    assert result["statusCode"] == 400


def test_unknown_connection_returns_401():
    from src.interfaces.websocket_handlers.default import handler

    connections = AsyncMock(get=AsyncMock(return_value=None))
    container = _make_container(connections=connections)
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"type": "PING"}), None)

    assert result["statusCode"] == 401


def test_unknown_message_type_returns_400():
    from src.interfaces.websocket_handlers.default import handler

    container = _make_container()
    with patch("src.interfaces.websocket_handlers.default.container", container):
        result = handler(_make_event({"type": "FIRE_LASER"}), None)

    assert result["statusCode"] == 400
