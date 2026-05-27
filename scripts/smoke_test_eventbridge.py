#!/usr/bin/env python3
"""Smoke test: EventBridge publisher against real AWS.

Usage:
    AWS_REGION=eu-central-1 EVENT_BUS_NAME=budes-dev python scripts/smoke_test_eventbridge.py

NOT run by pytest. Manual execution only.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.infrastructure.eventbridge.eventbridge_publisher import EventBridgePublisher

BUS_NAME = os.environ["EVENT_BUS_NAME"]
REGION = os.environ.get("AWS_REGION", "eu-central-1")


async def smoke_eventbridge() -> None:
    publisher = EventBridgePublisher(event_bus_name=BUS_NAME, region=REGION)

    print(f"[EventBridge] bus={BUS_NAME} region={REGION}")

    await publisher.publish(
        event_type="smoke.test.event",
        detail={"source": "smoke_test_eventbridge", "message": "hello from smoke test"},
    )
    print("  ✓ event published")

    print("[EventBridge] PASS")


if __name__ == "__main__":
    asyncio.run(smoke_eventbridge())
