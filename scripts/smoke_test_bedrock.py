#!/usr/bin/env python3
"""Smoke test: Bedrock generator against real AWS.

Usage:
    AWS_REGION=eu-central-1 DYNAMODB_TABLE=budes-dev \
    BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0 BEDROCK_REGION=eu-central-1 \
    python scripts/smoke_test_bedrock.py

NOT run by pytest. Manual execution only.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.infrastructure.ai.bedrock_generator import BedrockGenerator
from src.infrastructure.ai.prompt_cache import PromptCache
from src.infrastructure.clock.system_clock import SystemClock

TABLE = os.environ["DYNAMODB_TABLE"]
REGION = os.environ.get("AWS_REGION", "eu-central-1")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", REGION)
MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")


async def smoke_bedrock() -> None:
    clock = SystemClock()
    cache = PromptCache(
        table_name=TABLE,
        ttl_seconds=60,
        clock=clock,
        region=REGION,
    )
    generator = BedrockGenerator(model_id=MODEL_ID, region=BEDROCK_REGION, prompt_cache=cache)

    print(f"[Bedrock] model={MODEL_ID} region={BEDROCK_REGION}")

    prompt, options = await generator.generate_prompt(
        game="NEXT_GOAL_TIMING",
        recent_events=[],
        team_a="Bayern",
        team_b="Dortmund",
    )
    print(f"  ✓ prompt: {prompt!r}")
    print(f"  ✓ options: {options}")
    assert prompt, "empty prompt returned"

    print("[Bedrock] PASS")


if __name__ == "__main__":
    asyncio.run(smoke_bedrock())
