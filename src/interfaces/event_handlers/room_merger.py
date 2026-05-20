"""Scheduled Lambda: merge under-populated rooms."""

from __future__ import annotations

import logging
from typing import Any

from src.interfaces.shared.error_handler import lambda_handler
from src.interfaces.shared.lambda_response import success
from src.main import container

logger = logging.getLogger(__name__)


@lambda_handler
async def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Pair up under-populated active rooms and merge them."""
    merge_count = await container["use_cases"]["merge_rooms"].execute()
    logger.info("Room merge tick complete", extra={"merge_count": merge_count})
    return success()
