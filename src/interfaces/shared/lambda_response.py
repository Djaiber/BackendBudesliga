"""Standard Lambda HTTP response builders."""

from __future__ import annotations

import json
from typing import Any


def success(body: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"statusCode": 200, "body": json.dumps(body or {})}


def unauthorized(message: str = "Unauthorized") -> dict[str, Any]:
    return {"statusCode": 401, "body": json.dumps({"error": message})}


def bad_request(message: str) -> dict[str, Any]:
    return {"statusCode": 400, "body": json.dumps({"error": message})}


def server_error(message: str = "Internal error") -> dict[str, Any]:
    return {"statusCode": 500, "body": json.dumps({"error": message})}
