"""API Gateway $connect route handler."""

from __future__ import annotations

import logging
from typing import Any

from src.infrastructure.cognito.exceptions import InvalidTokenError
from src.interfaces.shared.error_handler import lambda_handler
from src.interfaces.shared.lambda_response import success, unauthorized
from src.main import container

logger = logging.getLogger(__name__)


@lambda_handler
async def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Validate Cognito token and store connection on $connect."""
    connection_id: str = event["requestContext"]["connectionId"]
    qs: dict[str, str] = event.get("queryStringParameters") or {}
    token: str | None = qs.get("token")

    if not token:
        logger.warning("Connect rejected: no token", extra={"connection_id": connection_id})
        return unauthorized("Token required")

    try:
        claims: dict[str, Any] = await container["cognito"].validate(token)
    except InvalidTokenError:
        logger.warning("Connect rejected: invalid token", extra={"connection_id": connection_id})
        return unauthorized("Invalid token")

    user_id: str = claims["sub"]
    user_name: str = (
        claims.get("name")
        or claims.get("email")
        or claims.get("cognito:username")
        or user_id
    )

    await container["connections"].put(
        conn_id=connection_id,
        user_id=user_id,
        user_name=user_name,
        room_id="",
        connected_at_ms=container["clock"].now_ms(),
    )

    logger.info(
        "Connection established",
        extra={"connection_id": connection_id, "user_id": user_id},
    )
    return success()
