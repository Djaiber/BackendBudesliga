#!/usr/bin/env python3
"""Run the replay engine locally without AWS.

Prints each event as it's published instead of calling EventBridge.
Useful for end-to-end smoke testing the replay logic.

Usage:
    python scripts/run_local_replay.py
    python scripts/run_local_replay.py --speed 600
    python scripts/run_local_replay.py --events scripts/output/events.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.clock.system_clock import SystemClock  # noqa: E402
from src.infrastructure.replay.replay_engine import ReplayEngine  # noqa: E402
from src.infrastructure.replay.xml_parser import ReplayParseError, parse_events  # noqa: E402

_DEFAULT_EVENTS_XML = (
    PROJECT_ROOT / "DataExploration" / "datos" / "Events_Anonym.xml"
)
_DEFAULT_EVENTS_JSON = PROJECT_ROOT / "scripts" / "output" / "events.json"


# ---------------------------------------------------------------------------
# PrintPublisher — implements EventPublisher protocol, prints to stdout
# ---------------------------------------------------------------------------


class PrintPublisher:
    """EventPublisher that prints events to stdout instead of calling EventBridge."""

    async def publish(self, source: str, detail_type: str, detail: dict[str, Any]) -> None:
        minute = detail.get("minute", 0)
        second = detail.get("second", 0)
        event_type = detail.get("event_type", "?")
        team = detail.get("team") or "-"
        player = detail.get("player") or "-"
        print(f"[{minute:02d}:{second:02d}] {event_type:<12} team={team:<6} player={player}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--speed",
        type=int,
        default=60,
        help="Speed factor: 60 = 1 match minute per real second (default: 60)",
    )
    parser.add_argument(
        "--events",
        type=str,
        default=None,
        help="Path to events JSON file (default: use XML source)",
    )
    return parser.parse_args()


def _load_events_from_json(path: str) -> list[Any]:
    """Load events from a pre-converted JSON file."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


async def _run(speed: int, events_path: str | None) -> int:
    """Run the replay engine and return exit code."""
    from src.domain.entities import MatchEvent

    # Load events
    if events_path:
        print(f"Loading events from JSON: {events_path}")
        try:
            raw = _load_events_from_json(events_path)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
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
    else:
        xml_path = str(_DEFAULT_EVENTS_XML)
        print(f"Parsing events from XML: {xml_path}")
        try:
            events = parse_events(xml_path)
        except (FileNotFoundError, ReplayParseError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    print(f"Loaded {len(events)} events  |  speed_factor={speed}")
    print(f"Estimated duration: ~{(events[-1].minute * 60 + events[-1].second) / speed:.1f}s")
    print("-" * 60)

    engine = ReplayEngine(
        events=events,
        publisher=PrintPublisher(),
        clock=SystemClock(),
        speed_factor=speed,
        source="connected-arena.replay",
        detail_type="MatchEvent",
    )

    try:
        await engine.run()
    except KeyboardInterrupt:
        print("\nInterrupted.")

    print("-" * 60)
    print(f"Replay complete ({len(events)} events).")
    return 0


def main() -> None:
    args = _parse_args()
    sys.exit(asyncio.run(_run(args.speed, args.events)))


if __name__ == "__main__":
    main()
