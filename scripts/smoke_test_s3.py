#!/usr/bin/env python3
"""Smoke test: S3 ReplayLoader against real AWS (bundesliga-replay-data bucket).

Usage:
    AWS_REGION=eu-central-1 S3_REPLAY_BUCKET=bundesliga-replay-data python scripts/smoke_test_s3.py

NOT run by pytest. Manual execution only.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.infrastructure.s3.replay_loader import ReplayLoader

BUCKET = os.environ.get("S3_REPLAY_BUCKET", "bundesliga-replay-data")
REGION = os.environ.get("AWS_REGION", "eu-central-1")


async def smoke_s3() -> None:
    loader = ReplayLoader(bucket=BUCKET, region=REGION, enable_cache=False)

    print(f"[S3] bucket={BUCKET} region={REGION}")

    events = await loader.load_events("events.json")
    print(f"  ✓ loaded {len(events)} events")
    assert len(events) > 0, "no events loaded"

    match_info = await loader.load_match_info("match_info.json")
    print(f"  ✓ loaded match info: {list(match_info.keys())}")
    assert match_info, "empty match info"

    print("[S3] PASS")


if __name__ == "__main__":
    asyncio.run(smoke_s3())
