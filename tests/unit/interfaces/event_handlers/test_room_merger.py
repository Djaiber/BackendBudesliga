"""Unit tests for room_merger scheduled handler."""

from unittest.mock import AsyncMock, patch


def _make_container(merge_count=0):
    return {
        "use_cases": {
            "merge_rooms": AsyncMock(execute=AsyncMock(return_value=merge_count)),
        }
    }


def test_merge_rooms_called_once_returns_200():
    from src.interfaces.event_handlers.room_merger import handler

    container = _make_container(merge_count=0)
    with patch("src.interfaces.event_handlers.room_merger.container", container):
        result = handler({}, None)

    assert result["statusCode"] == 200
    container["use_cases"]["merge_rooms"].execute.assert_awaited_once()


def test_merge_count_is_logged(caplog):
    import logging

    from src.interfaces.event_handlers.room_merger import handler

    container = _make_container(merge_count=3)
    with patch("src.interfaces.event_handlers.room_merger.container", container), \
            caplog.at_level(logging.INFO, logger="src.interfaces.event_handlers.room_merger"):
        handler({}, None)

    assert any("3" in r.message or "merge_count" in str(r.__dict__) for r in caplog.records)
