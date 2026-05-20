"""API Gateway $disconnect route handler."""

from __future__ import annotations

import logging
from typing import Any

from src.interfaces.shared.error_handler import lambda_handler
from src.interfaces.shared.lambda_response import success
from src.main import container

logger = logging.getLogger(__name__)


@lambda_handler
async def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Clean up connection and room membership on $disconnect."""
    connection_id: str = event["requestContext"]["connectionId"]

    conn: dict[str, Any] | None = await container["connections"].get(connection_id)
    if conn and conn.get("room_id"):
        await container["use_cases"]["leave_room"].execute(
            user_id=conn["user_id"],
            room_id=conn["room_id"],
        )

    await container["connections"].delete(connection_id)
    logger.info("Connection closed", extra={"connection_id": connection_id})
    return success()
