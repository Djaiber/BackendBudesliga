"""API Gateway $default route — message router."""

from __future__ import annotations

import json
import logging
from typing import Any

from src.interfaces.shared.error_handler import lambda_handler
from src.interfaces.shared.lambda_response import bad_request, success, unauthorized
from src.main import container

logger = logging.getLogger(__name__)


@lambda_handler
async def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Route inbound WebSocket messages by their 'type' field."""
    connection_id: str = event["requestContext"]["connectionId"]

    try:
        body: dict[str, Any] = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return bad_request("Malformed JSON")

    msg_type: str | None = body.get("type")
    if not msg_type:
        return bad_request("Missing type field")

    conn: dict[str, Any] | None = await container["connections"].get(connection_id)
    if not conn:
        return unauthorized("Unknown connection")

    user_id: str = conn["user_id"]
    user_name: str = conn.get("user_name") or user_id

    if msg_type == "PING":
        await container["broadcaster"].send_to_connection(
            connection_id, {"type": "PONG"}
        )
        return success()

    if msg_type == "JOIN_ROOM":
        result = await container["use_cases"]["join_room"].execute(
            user_id=user_id,
            player_name=user_name,
            connection_id=connection_id,
        )
        await container["connections"].update_room(connection_id, result.room.room_id)
        return success()

    if msg_type == "SUBMIT_PREDICTION":
        window_id: str | None = body.get("windowId")
        value: str | int | None = body.get("value")
        if not window_id or value is None:
            return bad_request("windowId and value required")
        result_pred = await container["use_cases"]["submit_prediction"].execute(
            window_id=window_id,
            user_id=user_id,
            value=value,
        )
        if not result_pred.success:
            return bad_request(result_pred.error or "rejected")
        return success()

    if msg_type == "EMOJI":
        emoji: str | None = body.get("emoji")
        room_id: str = conn.get("room_id") or ""
        if not emoji or not room_id:
            return bad_request("emoji and active room required")
        await container["use_cases"]["broadcast_emoji"].execute(
            room_id=room_id,
            user_id=user_id,
            emoji=emoji,
        )
        return success()

    logger.warning("Unknown message type", extra={"msg_type": msg_type})
    return bad_request(f"Unknown message type: {msg_type}")
