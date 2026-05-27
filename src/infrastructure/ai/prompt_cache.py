"""DynamoDB-backed prompt cache for Bedrock AI generator."""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import aioboto3

from src.domain.ports import Clock
from src.infrastructure.dynamodb import schema
from src.infrastructure.dynamodb.client import get_ddb_resource_kwargs

logger = logging.getLogger(__name__)


class PromptCache:
    """DynamoDB-backed cache for generated prompts.

    Caches (game, teams) → (prompt_text, options) to avoid redundant Bedrock calls.
    Items expire via DynamoDB TTL.
    """

    def __init__(
        self,
        table_name: str,
        ttl_seconds: int,
        clock: Clock,
        region: str,
        endpoint_url: str | None = None,
    ) -> None:
        self._table_name = table_name
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._session = aioboto3.Session()
        self._resource_kwargs = get_ddb_resource_kwargs(region, endpoint_url)

    def _make_key(self, game: str, team_a: str, team_b: str) -> str:
        raw = f"{game}:{team_a}:{team_b}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def get(self, game: str, team_a: str, team_b: str) -> tuple[str, tuple[str, ...] | None] | None:
        key = self._make_key(game, team_a, team_b)
        try:
            async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
                table = await ddb.Table(self._table_name)
                response = await table.get_item(
                    Key={"PK": schema.cache_pk(), "SK": schema.cache_sk(key)}
                )
                item = response.get("Item")
                if not item:
                    return None
                prompt_text: str = item["prompt_text"]
                options_raw: list[str] | None = item.get("options")
                options = tuple(options_raw) if options_raw else None
                return prompt_text, options
        except Exception as exc:
            logger.warning("PromptCache.get failed: %s", exc)
            return None

    async def put(
        self, game: str, team_a: str, team_b: str, value: tuple[str, tuple[str, ...] | None]
    ) -> None:
        key = self._make_key(game, team_a, team_b)
        prompt_text, options = value
        ttl = (self._clock.now_ms() // 1000) + self._ttl_seconds
        item: dict[str, Any] = {
            "PK": schema.cache_pk(),
            "SK": schema.cache_sk(key),
            "prompt_text": prompt_text,
            "ttl": ttl,
        }
        if options:
            item["options"] = list(options)
        try:
            async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
                table = await ddb.Table(self._table_name)
                await table.put_item(Item=item)
        except Exception as exc:
            logger.warning("PromptCache.put failed: %s", exc)
