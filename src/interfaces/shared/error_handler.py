"""Decorator that catches unhandled exceptions and returns a 500 response."""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from src.interfaces.shared.lambda_response import server_error

logger = logging.getLogger(__name__)

HandlerFunc = Callable[[dict[str, Any], object], Coroutine[Any, Any, dict[str, Any]]]
WrappedHandler = Callable[[dict[str, Any], object], dict[str, Any]]


def lambda_handler(func: HandlerFunc) -> WrappedHandler:
    """Wrap an async Lambda handler so it runs inside asyncio.run and catches exceptions."""

    @functools.wraps(func)
    def wrapper(event: dict[str, Any], context: object) -> dict[str, Any]:
        try:
            return asyncio.run(func(event, context))
        except Exception:
            lambda_name = getattr(context, "function_name", "unknown") if context else "unknown"
            request_id = getattr(context, "aws_request_id", "unknown") if context else "unknown"
            logger.exception(
                "Unhandled error in handler",
                extra={"lambda_name": lambda_name, "request_id": request_id},
            )
            return server_error()

    return wrapper
