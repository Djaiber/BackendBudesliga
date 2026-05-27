#!/usr/bin/env python3
"""Upload events.json to S3 and trigger replay engine to publish all events.

Usage:
    python scripts/upload_and_replay.py
    python scripts/upload_and_replay.py --speed 600  # 1 match minute = 100ms real time
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.entities import MatchEvent
from src.infrastructure.clock.system_clock import SystemClock
from src.infrastructure.eventbridge.eventbridge_publisher import EventBridgePublisher
from src.infrastructure.replay.replay_engine import ReplayEngine

EVENTS_JSON = PROJECT_ROOT / "scripts" / "output" / "events.json"
BUS_NAME = os.environ.get("EVENT_BUS_NAME", "connected-arena")
REGION = os.environ.get("AWS_REGION", "eu-central-1")


async def main(speed: int) -> None:
    # Load events
    with open(EVENTS_JSON, encoding="utf-8") as f:
        raw = json.load(f)

    events = [
        MatchEvent(
            event_id=e["event_id"],
            minute=e["minute"],
            second=e["second"],
            event_type=e["event_type"],
            team=e.get("team") or "",
            player=e.get("player"),
            x_position=e.get("x_position"),
            y_position=e.get("y_position"),
            metadata=e.get("metadata", {}),
        )
        for e in raw
    ]

    print(f"Loaded {len(events)} events from {EVENTS_JSON}")

    # Count by type
    from collections import Counter
    counts = Counter(e.event_type for e in events)
    print("Event type distribution:")
    for event_type, count in sorted(counts.items()):
        print(f"  {event_type}: {count}")

    # Create publisher and replay engine
    publisher = EventBridgePublisher(event_bus_name=BUS_NAME, region=REGION)
    clock = SystemClock()
    engine = ReplayEngine(
        events=events,
        publisher=publisher,
        clock=clock,
        speed_factor=speed,
        source="replay",
        detail_type="MatchEvent",
    )

    print(f"\nStarting replay with speed_factor={speed} (1 match min = {60000/speed:.1f}ms real time)")
    print(f"Publishing to EventBridge bus: {BUS_NAME} (region: {REGION})")
    print("Press Ctrl+C to stop\n")

    try:
        await engine.run()
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        await engine.stop()

    print(f"\n✓ Replay complete - published {len(events)} events")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--speed", type=int, default=600, help="Speed factor (default: 600 = 1 match min in 100ms)")
    args = parser.parse_args()

    asyncio.run(main(args.speed))
