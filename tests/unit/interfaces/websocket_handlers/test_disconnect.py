"""Unit tests for $disconnect handler."""

from unittest.mock import AsyncMock, patch


def _make_event(connection_id="conn1"):
    return {"requestContext": {"connectionId": connection_id}}


def _make_container(connections=None, use_cases=None):
    return {
        "connections": connections or AsyncMock(),
        "use_cases": use_cases or {"leave_room": AsyncMock()},
    }


def test_disconnect_with_room_calls_leave_room():
    from src.interfaces.websocket_handlers.disconnect import handler

    leave_room = AsyncMock()
    connections = AsyncMock(
        get=AsyncMock(return_value={"user_id": "u1", "room_id": "room99"}),
        delete=AsyncMock(),
    )
    container = _make_container(connections=connections, use_cases={"leave_room": leave_room})
    with patch("src.interfaces.websocket_handlers.disconnect.container", container):
        result = handler(_make_event(), None)

    assert result["statusCode"] == 200
    leave_room.execute.assert_awaited_once_with(user_id="u1", room_id="room99")
    connections.delete.assert_awaited_once_with("conn1")


def test_disconnect_without_room_skips_leave_room():
    from src.interfaces.websocket_handlers.disconnect import handler

    leave_room = AsyncMock()
    connections = AsyncMock(
        get=AsyncMock(return_value={"user_id": "u1", "room_id": ""}),
        delete=AsyncMock(),
    )
    container = _make_container(connections=connections, use_cases={"leave_room": leave_room})
    with patch("src.interfaces.websocket_handlers.disconnect.container", container):
        result = handler(_make_event(), None)

    assert result["statusCode"] == 200
    leave_room.execute.assert_not_awaited()
    connections.delete.assert_awaited_once()


def test_disconnect_unknown_connection_still_returns_200():
    from src.interfaces.websocket_handlers.disconnect import handler

    connections = AsyncMock(get=AsyncMock(return_value=None), delete=AsyncMock())
    container = _make_container(connections=connections)
    with patch("src.interfaces.websocket_handlers.disconnect.container", container):
        result = handler(_make_event(), None)

    assert result["statusCode"] == 200
    connections.delete.assert_awaited_once()
