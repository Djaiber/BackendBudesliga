"""AWS Bedrock AI generator implementing the AIGenerator port."""

from __future__ import annotations

import json
import logging
from typing import Any

import aioboto3

from src.domain.entities import MatchEvent
from src.infrastructure.ai.prompt_cache import PromptCache

logger = logging.getLogger(__name__)

_FALLBACK_PROMPTS: dict[str, tuple[str, tuple[str, ...] | None]] = {
    "NEXT_GOAL_TIMING": (
        "When will the next goal be scored?",
        ("0-15 min", "15-30 min", "30-45 min", "45+ min"),
    ),
    "CORNERS_IN_INTERVAL": (
        "How many corners in the next 15 minutes?",
        ("0", "1", "2", "3+"),
    ),
    "GOAL_IN_TIME_WINDOW": (
        "Will there be a goal in the next 10 minutes?",
        ("Yes", "No"),
    ),
}


class BedrockGenerator:
    """AWS Bedrock adapter for the AIGenerator port.

    Generates contextual prediction prompts using Claude via Bedrock.
    Falls back to static prompts on error or when Bedrock is unavailable.
    """

    def __init__(self, model_id: str, region: str, prompt_cache: PromptCache) -> None:
        self._model_id = model_id
        self._region = region
        self._prompt_cache = prompt_cache
        self._session = aioboto3.Session()

    async def generate_prompt(
        self,
        game: str,
        recent_events: list[MatchEvent],
        team_a: str,
        team_b: str,
    ) -> tuple[str, tuple[str, ...] | None]:
        cached = await self._prompt_cache.get(game, team_a, team_b)
        if cached is not None:
            return cached

        result = await self._call_bedrock(game, recent_events, team_a, team_b)
        await self._prompt_cache.put(game, team_a, team_b, result)
        return result

    async def _call_bedrock(
        self,
        game: str,
        recent_events: list[MatchEvent],
        team_a: str,
        team_b: str,
    ) -> tuple[str, tuple[str, ...] | None]:
        fallback = _FALLBACK_PROMPTS.get(game, ("What will happen next?", None))
        events_summary = ", ".join(
            f"{e.event_type}@{e.minute}:{e.second:02d}" for e in recent_events[-5:]
        )
        body_payload: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 256,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Generate a short prediction question for a football mini-game.\n"
                        f"Teams: {team_a} vs {team_b}\n"
                        f"Game type: {game}\n"
                        f"Recent events: {events_summary or 'none'}\n"
                        f"Return JSON: {{\"prompt\": \"...\", \"options\": [\"...\", ...]}}"
                    ),
                }
            ],
        }
        try:
            async with self._session.client(
                "bedrock-runtime",
                region_name=self._region,
            ) as client:
                response = await client.invoke_model(
                    modelId=self._model_id,
                    body=json.dumps(body_payload).encode(),
                    contentType="application/json",
                    accept="application/json",
                )
                body_bytes: bytes = await response["body"].read()
                parsed: dict[str, Any] = json.loads(body_bytes)
                content_text: str = parsed["content"][0]["text"]
                data: dict[str, Any] = json.loads(content_text)
                prompt_text: str = data["prompt"]
                raw_options: list[str] | None = data.get("options")
                options = tuple(raw_options) if raw_options else None
                return prompt_text, options
        except Exception as exc:
            logger.warning("Bedrock call failed for game=%s, using fallback: %s", game, exc)
            return fallback
