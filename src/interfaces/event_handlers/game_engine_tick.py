"""Scheduled Lambda: open/close prediction windows for each active room."""

from __future__ import annotations

import logging
import random
from typing import Any

from src.domain.entities import Room
from src.interfaces.shared.error_handler import lambda_handler
from src.interfaces.shared.lambda_response import success
from src.main import container

logger = logging.getLogger(__name__)

_WINDOW_OPEN_PROBABILITY = 0.3


def _should_open_window(room: Room) -> bool:
    """Return True with ~30% probability to avoid flooding rooms with windows."""
    return len(room.players) > 0 and random.random() < _WINDOW_OPEN_PROBABILITY


@lambda_handler
async def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """For each active room: close expired windows, maybe open a new one."""
    rooms = await container["use_cases"]["list_active_rooms"].execute()

    for room in rooms:
        closed = await container["use_cases"]["close_expired_windows"].execute(room.room_id)
        if closed:
            logger.info("Closed expired windows", extra={"room_id": room.room_id, "closed": closed})

        if not closed and _should_open_window(room):
            await container["use_cases"]["open_window"].execute(
                room_id=room.room_id,
                recent_events=[],
                correct_answer="TBD",
                team_a="Home",
                team_b="Away",
            )
            logger.info("Opened prediction window", extra={"room_id": room.room_id})

    return success()
