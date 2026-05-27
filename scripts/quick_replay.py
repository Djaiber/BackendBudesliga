#!/usr/bin/env python3
"""Quick replay script - publish sample diverse events to EventBridge NOW.

This script sends a variety of event types immediately without waiting for
the full S3 replay Lambda to build.

Usage:
    python scripts/quick_replay.py
"""

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.eventbridge.eventbridge_publisher import EventBridgePublisher

BUS_NAME = os.environ.get("EVENT_BUS_NAME", "connected-arena-events")
REGION = os.environ.get("AWS_REGION", "eu-central-1")


async def main() -> None:
    publisher = EventBridgePublisher(event_bus_name=BUS_NAME, region=REGION)

    print(f"Publishing diverse events to {BUS_NAME}...")

    events = [
        {"event_id": "quick-001", "minute": 5, "second": 0, "event_type": "KICK_OFF", "team": "Bayern"},
        {"event_id": "quick-002", "minute": 8, "second": 15, "event_type": "GOAL", "team": "Bayern", "player": "Müller"},
        {"event_id": "quick-003", "minute": 12, "second": 30, "event_type": "YELLOW", "team": "Dortmund", "player": "Reus"},
        {"event_id": "quick-004", "minute": 18, "second": 0, "event_type": "FOUL", "team": "Bayern", "player": None},
        {"event_id": "quick-005", "minute": 22, "second": 45, "event_type": "SHOT", "team": "Dortmund", "player": "Haaland"},
        {"event_id": "quick-006", "minute": 28, "second": 10, "event_type": "CORNER_KICK", "team": "Bayern", "player": None},
        {"event_id": "quick-007", "minute": 35, "second": 0, "event_type": "SUB", "team": "Bayern", "player": "Sané"},
        {"event_id": "quick-008", "minute": 40, "second": 30, "event_type": "FREE_KICK", "team": "Dortmund", "player": None},
        {"event_id": "quick-009", "minute": 45, "second": 0, "event_type": "FINAL_WHISTLE", "team": None, "player": None},
    ]

    for event in events:
        payload = {
            "event_id": event["event_id"],
            "minute": event["minute"],
            "second": event["second"],
            "event_type": event["event_type"],
            "team": event.get("team") or "",
            "player": event.get("player"),
            "x_position": None,
            "y_position": None,
            "metadata": {},
        }
        await publisher.publish("replay", "MatchEvent", payload)
        print(f"  ✓ {event['event_type']} at {event['minute']}:{event['second']:02d}")
        await asyncio.sleep(2)  # 2 seconds between events

    print(f"\n✓ Published {len(events)} diverse events")
    print("Check your frontend at https://main.d2zmf07qpbph28.amplifyapp.com/live-predict/match-001")


if __name__ == "__main__":
    asyncio.run(main())
