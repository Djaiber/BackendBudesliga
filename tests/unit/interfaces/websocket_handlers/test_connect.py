"""Unit tests for $connect handler."""

from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.cognito.exceptions import InvalidTokenError


def _make_event(connection_id="conn1", token="valid-token"):
    return {
        "requestContext": {"connectionId": connection_id},
        "queryStringParameters": {"token": token} if token else None,
    }


def _make_container(cognito=None, connections=None, clock=None):
    mock_clock = clock or MagicMock(now_ms=MagicMock(return_value=1_000_000))
    mock_connections = connections or AsyncMock()
    mock_cognito = cognito or AsyncMock(
        validate=AsyncMock(return_value={"sub": "user1", "email": "user@test.com"})
    )
    return {
        "clock": mock_clock,
        "connections": mock_connections,
        "cognito": mock_cognito,
    }


def test_connect_valid_token_returns_200():
    from src.interfaces.websocket_handlers.connect import handler

    container = _make_container()
    with patch("src.interfaces.websocket_handlers.connect.container", container):
        result = handler(_make_event(), None)

    assert result["statusCode"] == 200


def test_connect_stores_connection_with_user_info():
    from src.interfaces.websocket_handlers.connect import handler

    connections = AsyncMock()
    container = _make_container(connections=connections)
    with patch("src.interfaces.websocket_handlers.connect.container", container):
        handler(_make_event(connection_id="conn42", token="tok"), None)

    connections.put.assert_awaited_once()
    kwargs = connections.put.call_args.kwargs
    assert kwargs["conn_id"] == "conn42"
    assert kwargs["user_id"] == "user1"
    assert kwargs["user_name"] == "user@test.com"
    assert kwargs["room_id"] == ""


def test_connect_missing_token_returns_401():
    from src.interfaces.websocket_handlers.connect import handler

    container = _make_container()
    with patch("src.interfaces.websocket_handlers.connect.container", container):
        result = handler(_make_event(token=None), None)

    assert result["statusCode"] == 401


def test_connect_invalid_token_returns_401():
    from src.interfaces.websocket_handlers.connect import handler

    cognito = AsyncMock(validate=AsyncMock(side_effect=InvalidTokenError("bad")))
    container = _make_container(cognito=cognito)
    with patch("src.interfaces.websocket_handlers.connect.container", container):
        result = handler(_make_event(), None)

    assert result["statusCode"] == 401


def test_connect_repository_error_returns_500():
    from src.interfaces.websocket_handlers.connect import handler

    connections = AsyncMock(put=AsyncMock(side_effect=RuntimeError("DDB down")))
    container = _make_container(connections=connections)
    with patch("src.interfaces.websocket_handlers.connect.container", container):
        result = handler(_make_event(), None)

    assert result["statusCode"] == 500
