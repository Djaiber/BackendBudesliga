"""Integration tests for PromptCache (DynamoDB-backed)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.ai.prompt_cache import PromptCache
from tests.unit.application.fakes.fake_clock import FakeClock

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock(initial_ms=1_000_000)


@pytest.fixture
def cache(fake_clock: FakeClock) -> PromptCache:
    return PromptCache(
        table_name="test-table",
        ttl_seconds=60,
        clock=fake_clock,
        region="eu-central-1",
        endpoint_url=None,
    )


def _make_mock_table(get_item_response: dict) -> AsyncMock:
    table = AsyncMock()
    table.get_item = AsyncMock(return_value=get_item_response)
    table.put_item = AsyncMock(return_value={})
    return table


def _patch_session(cache: PromptCache, table: AsyncMock) -> None:
    resource_cm = AsyncMock()
    resource_cm.__aenter__ = AsyncMock(return_value=resource_cm)
    resource_cm.__aexit__ = AsyncMock(return_value=None)
    resource_cm.Table = AsyncMock(return_value=table)
    cache._session.resource = MagicMock(return_value=resource_cm)


# ---------------------------------------------------------------------------
# get() — cache miss
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_returns_none_on_cache_miss(cache: PromptCache, fake_clock: FakeClock) -> None:
    table = _make_mock_table({"Item": None} if False else {})
    _patch_session(cache, table)

    result = await cache.get("NEXT_GOAL_TIMING", "Bayern", "Dortmund")

    assert result is None


# ---------------------------------------------------------------------------
# get() — cache hit with options
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_returns_cached_prompt_with_options(
    cache: PromptCache, fake_clock: FakeClock
) -> None:
    table = _make_mock_table(
        {
            "Item": {
                "PK": "CACHE#PROMPT",
                "SK": "CACHE#abc123",
                "prompt_text": "Will there be a goal?",
                "options": ["Yes", "No"],
                "ttl": 9999,
            }
        }
    )
    _patch_session(cache, table)

    result = await cache.get("GOAL_IN_TIME_WINDOW", "Bayern", "Dortmund")

    assert result is not None
    prompt_text, options = result
    assert prompt_text == "Will there be a goal?"
    assert options == ("Yes", "No")


# ---------------------------------------------------------------------------
# get() — cache hit without options
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_returns_cached_prompt_without_options(cache: PromptCache) -> None:
    table = _make_mock_table(
        {
            "Item": {
                "PK": "CACHE#PROMPT",
                "SK": "CACHE#abc123",
                "prompt_text": "Open ended question?",
                "ttl": 9999,
            }
        }
    )
    _patch_session(cache, table)

    result = await cache.get("CORNERS_IN_INTERVAL", "Bayern", "Dortmund")

    assert result is not None
    prompt_text, options = result
    assert prompt_text == "Open ended question?"
    assert options is None


# ---------------------------------------------------------------------------
# get() — DynamoDB error returns None (silent failure)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_returns_none_on_dynamodb_error(cache: PromptCache) -> None:
    table = AsyncMock()
    table.get_item = AsyncMock(side_effect=Exception("DynamoDB unavailable"))
    _patch_session(cache, table)

    result = await cache.get("NEXT_GOAL_TIMING", "Bayern", "Dortmund")

    assert result is None


# ---------------------------------------------------------------------------
# put() — stores item with TTL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_stores_item_with_ttl(cache: PromptCache, fake_clock: FakeClock) -> None:
    table = AsyncMock()
    table.put_item = AsyncMock(return_value={})
    _patch_session(cache, table)

    await cache.put("NEXT_GOAL_TIMING", "Bayern", "Dortmund", ("When will next goal?", ("0-15", "15-30")))

    table.put_item.assert_awaited_once()
    call_kwargs = table.put_item.call_args[1]
    item = call_kwargs["Item"]
    assert item["prompt_text"] == "When will next goal?"
    assert item["options"] == ["0-15", "15-30"]
    assert item["ttl"] == 1000 + 60  # now_ms // 1000 + ttl_seconds


# ---------------------------------------------------------------------------
# put() — stores item without options
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_stores_item_without_options(cache: PromptCache) -> None:
    table = AsyncMock()
    table.put_item = AsyncMock(return_value={})
    _patch_session(cache, table)

    await cache.put("NEXT_GOAL_TIMING", "Bayern", "Dortmund", ("Open question?", None))

    table.put_item.assert_awaited_once()
    item = table.put_item.call_args[1]["Item"]
    assert "options" not in item


# ---------------------------------------------------------------------------
# put() — DynamoDB error is swallowed (silent failure)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_put_swallows_dynamodb_error(cache: PromptCache) -> None:
    table = AsyncMock()
    table.put_item = AsyncMock(side_effect=Exception("write failed"))
    _patch_session(cache, table)

    # Should not raise
    await cache.put("NEXT_GOAL_TIMING", "Bayern", "Dortmund", ("Question?", None))


# ---------------------------------------------------------------------------
# _make_key determinism
# ---------------------------------------------------------------------------


def test_make_key_is_deterministic(cache: PromptCache) -> None:
    key1 = cache._make_key("GAME", "TeamA", "TeamB")
    key2 = cache._make_key("GAME", "TeamA", "TeamB")
    assert key1 == key2
    assert len(key1) == 16


def test_make_key_differs_for_different_inputs(cache: PromptCache) -> None:
    key1 = cache._make_key("GAME", "TeamA", "TeamB")
    key2 = cache._make_key("GAME", "TeamB", "TeamA")
    assert key1 != key2
