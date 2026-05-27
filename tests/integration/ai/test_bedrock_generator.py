"""Integration tests for BedrockGenerator."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.entities import MatchEvent
from src.infrastructure.ai.bedrock_generator import BedrockGenerator
from src.infrastructure.ai.prompt_cache import PromptCache

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_event(event_type: str = "GOAL", minute: int = 10, second: int = 0) -> MatchEvent:
    return MatchEvent(
        event_id="evt-1",
        minute=minute,
        second=second,
        event_type=event_type,
        team="home",
        player=None,
        x_position=None,
        y_position=None,
        metadata={},
    )


def make_bedrock_response(prompt: str, options: list[str] | None = None) -> dict:
    content_text = json.dumps({"prompt": prompt, "options": options} if options else {"prompt": prompt})
    return {
        "content": [{"text": content_text}]
    }


@pytest.fixture
def mock_prompt_cache() -> AsyncMock:
    cache = AsyncMock(spec=PromptCache)
    cache.get = AsyncMock(return_value=None)
    cache.put = AsyncMock(return_value=None)
    return cache


@pytest.fixture
def generator(mock_prompt_cache: AsyncMock) -> BedrockGenerator:
    return BedrockGenerator(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        region="eu-central-1",
        prompt_cache=mock_prompt_cache,
    )


def _patch_bedrock_client(generator: BedrockGenerator, response_body: dict) -> None:
    body_mock = AsyncMock()
    body_mock.read = AsyncMock(return_value=json.dumps(response_body).encode())

    client_mock = AsyncMock()
    client_mock.invoke_model = AsyncMock(return_value={"body": body_mock})
    client_mock.__aenter__ = AsyncMock(return_value=client_mock)
    client_mock.__aexit__ = AsyncMock(return_value=None)

    generator._session.client = MagicMock(return_value=client_mock)


# ---------------------------------------------------------------------------
# Cache hit — no Bedrock call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_prompt_returns_cached_result(
    generator: BedrockGenerator, mock_prompt_cache: AsyncMock
) -> None:
    mock_prompt_cache.get = AsyncMock(return_value=("Cached question?", ("A", "B")))

    result = await generator.generate_prompt("NEXT_GOAL_TIMING", [], "Bayern", "Dortmund")

    assert result == ("Cached question?", ("A", "B"))
    generator._session.client = MagicMock()  # ensure not called
    mock_prompt_cache.put.assert_not_awaited()


# ---------------------------------------------------------------------------
# Bedrock success — result cached
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_prompt_calls_bedrock_on_cache_miss(
    generator: BedrockGenerator, mock_prompt_cache: AsyncMock
) -> None:
    bedrock_response = {
        "content": [{"text": json.dumps({"prompt": "When next goal?", "options": ["<15", "15-30", "30+"]})}]
    }
    _patch_bedrock_client(generator, bedrock_response)

    result = await generator.generate_prompt(
        "NEXT_GOAL_TIMING", [make_event()], "Bayern", "Dortmund"
    )

    assert result[0] == "When next goal?"
    assert result[1] == ("<15", "15-30", "30+")
    mock_prompt_cache.put.assert_awaited_once()


# ---------------------------------------------------------------------------
# Bedrock success — options absent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_prompt_handles_no_options_in_response(
    generator: BedrockGenerator, mock_prompt_cache: AsyncMock
) -> None:
    bedrock_response = {
        "content": [{"text": json.dumps({"prompt": "Open question?"})}]
    }
    _patch_bedrock_client(generator, bedrock_response)

    result = await generator.generate_prompt("NEXT_GOAL_TIMING", [], "Bayern", "Dortmund")

    assert result[0] == "Open question?"
    assert result[1] is None


# ---------------------------------------------------------------------------
# Bedrock failure — fallback prompt returned
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_prompt_falls_back_on_bedrock_error(
    generator: BedrockGenerator, mock_prompt_cache: AsyncMock
) -> None:
    client_mock = AsyncMock()
    client_mock.invoke_model = AsyncMock(side_effect=Exception("Bedrock unavailable"))
    client_mock.__aenter__ = AsyncMock(return_value=client_mock)
    client_mock.__aexit__ = AsyncMock(return_value=None)
    generator._session.client = MagicMock(return_value=client_mock)

    result = await generator.generate_prompt(
        "NEXT_GOAL_TIMING", [], "Bayern", "Dortmund"
    )

    assert "goal" in result[0].lower()
    assert result[1] is not None


# ---------------------------------------------------------------------------
# Bedrock failure — unknown game gets generic fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_prompt_falls_back_for_unknown_game(
    generator: BedrockGenerator,
) -> None:
    client_mock = AsyncMock()
    client_mock.invoke_model = AsyncMock(side_effect=Exception("error"))
    client_mock.__aenter__ = AsyncMock(return_value=client_mock)
    client_mock.__aexit__ = AsyncMock(return_value=None)
    generator._session.client = MagicMock(return_value=client_mock)

    result = await generator.generate_prompt("UNKNOWN_GAME", [], "Bayern", "Dortmund")

    assert isinstance(result[0], str)
    assert len(result[0]) > 0


# ---------------------------------------------------------------------------
# Recent events summary included in request body
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_prompt_includes_recent_events_in_body(
    generator: BedrockGenerator, mock_prompt_cache: AsyncMock
) -> None:
    captured_body: list[dict] = []

    async def fake_invoke_model(**kwargs) -> dict:
        body_bytes: bytes = kwargs["body"]
        captured_body.append(json.loads(body_bytes))
        body_mock = AsyncMock()
        body_mock.read = AsyncMock(
            return_value=json.dumps({"content": [{"text": json.dumps({"prompt": "Q?", "options": ["A", "B"]})}]}).encode()
        )
        return {"body": body_mock}

    client_mock = AsyncMock()
    client_mock.invoke_model = AsyncMock(side_effect=fake_invoke_model)
    client_mock.__aenter__ = AsyncMock(return_value=client_mock)
    client_mock.__aexit__ = AsyncMock(return_value=None)
    generator._session.client = MagicMock(return_value=client_mock)

    events = [make_event("GOAL", 5, 30), make_event("CORNER_KICK", 8, 0)]
    await generator.generate_prompt("NEXT_GOAL_TIMING", events, "Bayern", "Dortmund")

    assert captured_body
    content = captured_body[0]["messages"][0]["content"]
    assert "GOAL@5:30" in content
    assert "CORNER_KICK@8:00" in content
