"""Scheduled Lambda: load events from S3 and replay them to EventBridge.

This Lambda runs periodically (or on-demand) to:
1. Load events from s3://bundesliga-replay-data/events.json
2. Publish them to EventBridge using ReplayEngine at high speed
3. Cache loaded events in memory for subsequent invocations

Environment variables:
- REPLAY_BUCKET: S3 bucket name (default: bundesliga-replay-data)
- REPLAY_KEY: S3 object key (default: events.json)
- REPLAY_SPEED: Speed factor for replay (default: 600 = 1 match min in 100ms)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from src.infrastructure.clock.system_clock import SystemClock
from src.infrastructure.eventbridge.eventbridge_publisher import EventBridgePublisher
from src.infrastructure.replay.replay_engine import ReplayEngine
from src.infrastructure.s3.replay_loader import ReplayLoader
from src.interfaces.shared.error_handler import lambda_handler
from src.interfaces.shared.lambda_response import success
from src.main import container

logger = logging.getLogger(__name__)

# Module-level cache persists across warm invocations
_replay_loader: ReplayLoader | None = None
_replay_engine: ReplayEngine | None = None


def _get_replay_loader() -> ReplayLoader:
    """Get or create ReplayLoader singleton."""
    global _replay_loader
    if _replay_loader is None:
        bucket = os.environ.get("REPLAY_BUCKET", "bundesliga-replay-data")
        region = container["config"].aws_region
        # Disable cache for replay Lambda - it runs infrequently and we want fresh data
        _replay_loader = ReplayLoader(bucket=bucket, region=region, enable_cache=False)
        logger.info(f"Initialized ReplayLoader for bucket={bucket}")
    return _replay_loader


@lambda_handler
async def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    """Load events from S3 and replay them to EventBridge at high speed."""
    global _replay_engine

    # Get config
    bucket = os.environ.get("REPLAY_BUCKET", "bundesliga-replay-data")
    key = os.environ.get("REPLAY_KEY", "events.json")
    speed = int(os.environ.get("REPLAY_SPEED", "600"))

    logger.info(
        f"Starting S3 replay: bucket={bucket}, key={key}, speed={speed}x",
        extra={"bucket": bucket, "key": key, "speed": speed},
    )

    # Load events from S3 (cached after first load)
    loader = _get_replay_loader()
    events = await loader.load_events(key)

    if not events:
        logger.warning("No events loaded from S3")
        return success({"message": "No events to replay"})

    logger.info(f"Loaded {len(events)} events from S3 (cache_size={loader.get_cache_size()})")

    # Count events by type for logging
    from collections import Counter

    type_counts = Counter(e.event_type for e in events)
    logger.info(f"Event type distribution: {dict(type_counts)}")

    # Create replay engine (reuse EventBridge publisher from container)
    clock = SystemClock()
    publisher = EventBridgePublisher(
        event_bus_name=container["config"].event_bus_name,
        region=container["config"].aws_region,
    )

    _replay_engine = ReplayEngine(
        events=events,
        publisher=publisher,
        clock=clock,
        speed_factor=speed,
        source="replay",
        detail_type="MatchEvent",
    )

    logger.info(f"Starting replay of {len(events)} events at {speed}x speed")

    # Run replay (blocking - publishes all events sequentially)
    await _replay_engine.run()

    logger.info(f"Replay complete - published {len(events)} events to EventBridge")

    return success(
        {
            "message": "Replay complete",
            "events_published": len(events),
            "event_types": dict(type_counts),
        }
    )
