"""EventBridge consumer for MatchEvent detail-type."""

from __future__ import annotations

import logging
from typing import Any

from src.domain.entities import MatchEvent
from src.interfaces.shared.error_handler import lambda_handler
from src.interfaces.shared.lambda_response import bad_request, success
from src.main import container

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ("event_id", "minute", "second", "event_type", "team")


@lambda_handler
async def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Consume one MatchEvent from EventBridge and broadcast it to all rooms."""
    detail: dict[str, Any] = event.get("detail") or {}

    missing = [f for f in _REQUIRED_FIELDS if f not in detail]
    if missing:
        return bad_request(f"Missing required fields: {missing}")

    try:
        match_event = MatchEvent(
            event_id=str(detail["event_id"]),
            minute=int(detail["minute"]),
            second=int(detail["second"]),
            event_type=str(detail["event_type"]),
            team=str(detail["team"]),
            player=detail.get("player"),
            x_position=float(detail["x_position"]) if detail.get("x_position") is not None else None,
            y_position=float(detail["y_position"]) if detail.get("y_position") is not None else None,
            metadata=detail.get("metadata") or {},
        )
    except (ValueError, TypeError) as exc:
        return bad_request(f"Invalid event detail: {exc}")

    await container["use_cases"]["handle_match_event"].execute(match_event)
    return success()
