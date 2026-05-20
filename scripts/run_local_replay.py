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
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dateutil.parser import parse as _parse_dt

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.infrastructure.clock.system_clock import SystemClock  # noqa: E402
from src.infrastructure.replay.replay_engine import ReplayEngine  # noqa: E402
from src.infrastructure.replay.xml_parser import ReplayParseError, parse_events  # noqa: E402

_DEFAULT_EVENTS_XML = (
    PROJECT_ROOT / "DataExploration" / "datos" / "Events_Anonym.xml"
)
_DEFAULT_EVENTS_JSON = PROJECT_ROOT / "scripts" / "output" / "events.json"
_MATCH_INFO_JSON = PROJECT_ROOT / "scripts" / "output" / "match_info.json"
_KPI_JSON = PROJECT_ROOT / "scripts" / "output" / "kpi.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _deep_find_value(data: Any, keys: list[str]) -> str | None:
    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key]:
                return str(data[key])
        for value in data.values():
            nested = _deep_find_value(value, keys)
            if nested:
                return nested
    return None


# ---------------------------------------------------------------------------
# Lookup builders — resolve IDs to human-readable names
# ---------------------------------------------------------------------------


def _load_match_lookups() -> tuple[dict[str, str], dict[str, str]]:
    """Return (team_id→code, player_id→display) from match_info.json."""
    teams: dict[str, str] = {}
    players: dict[str, str] = {}
    try:
        with open(_MATCH_INFO_JSON, encoding="utf-8") as fh:
            info = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return teams, players

    for role in ("home_team", "guest_team"):
        team = info.get(role, {})
        tid = team.get("team_id", "")
        if tid:
            teams[tid] = team.get("three_letter_code") or team.get("short_name") or tid
        for p in team.get("players", []):
            pid = p.get("player_id", "")
            if not pid:
                continue
            name = p.get("short_name") or f"{p.get('first_name','')} {p.get('last_name','')}".strip()
            pos = p.get("position", "")
            players[pid] = f"{name} ({pos})" if pos else name

    return teams, players


def _load_kpi_lookup() -> dict[str, dict[str, Any]]:
    """Return event_id→kpi_entry from kpi.json."""
    try:
        with open(_KPI_JSON, encoding="utf-8") as fh:
            raw: dict[str, Any] = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    # kpi.json is now indexed directly by EventId
    return {k: v for k, v in raw.items() if isinstance(v, dict)}


# ---------------------------------------------------------------------------
# KPI formatting — pick the most relevant metric per event type
# ---------------------------------------------------------------------------

_KPI_FIELDS_BY_TYPE: dict[str, list[tuple[str, str]]] = {
    "GOAL":        [("xG", "xG"), ("ShotResult", "result"), ("AngleToGoal", "angle°")],
    "SHOT":        [("xG", "xG"), ("ShotResult", "result"), ("DistanceToGoal", "dist")],
    "PASS":        [("xP", "xP"), ("Distance", "dist"), ("PressureOnPlayer", "press"), ("ByPassedDefenders", "bypassed")],
    "CROSS":       [("xP", "xP"), ("Distance", "dist"), ("PressureOnPlayer", "press")],
    "FOUL":        [("IsFoul", "foul"), ("PressureOnPlayer", "press")],
    "CORNER_KICK": [("xP", "xP")],
    "FREE_KICK":   [("xP", "xP"), ("DistanceToGoal", "dist")],
    "THROW_IN":    [("xP", "xP")],
}


def _fmt_kpi(event_id: str, event_type: str, kpi_lookup: dict[str, dict[str, Any]]) -> str:
    kpi = kpi_lookup.get(event_id)
    if not kpi:
        return ""
    fields = _KPI_FIELDS_BY_TYPE.get(event_type, [])
    if not fields:
        return ""
    parts = []
    for kpi_key, label in fields:
        val = kpi.get(kpi_key)
        if val is not None and val != "":
            try:
                fval = float(val)
                parts.append(f"{label}={fval:.2f}")
            except (ValueError, TypeError):
                parts.append(f"{label}={val}")
    return "  " + "  ".join(parts) if parts else ""


# ---------------------------------------------------------------------------
# PrintPublisher — implements EventPublisher protocol, prints to stdout
# ---------------------------------------------------------------------------

# Event-type icons for quick scanning
_ICONS: dict[str, str] = {
    "GOAL": "GOAL >>>",
    "SHOT": "SHOT    ",
    "YELLOW": "YELLOW  ",
    "RED": "RED     ",
    "SUB": "SUB     ",
    "FOUL": "FOUL    ",
}


class PrintPublisher:
    """EventPublisher that resolves IDs to names and shows KPIs."""

    def __init__(
        self,
        team_lookup: dict[str, str],
        player_lookup: dict[str, str],
        kpi_lookup: dict[str, dict[str, Any]],
    ) -> None:
        self._teams = team_lookup
        self._players = player_lookup
        self._kpis = kpi_lookup

    def _resolve_team(self, detail: dict[str, Any]) -> str:
        raw = detail.get("team") or ""
        if raw:
            return self._teams.get(raw, raw)
        meta = detail.get("metadata") or {}
        for key in ("Team", "TeamId", "WinnerTeam", "FoulerTeam"):
            val = _deep_find_value(meta, [key])
            if val:
                return self._teams.get(val, val)
        return "-"

    def _resolve_player(self, detail: dict[str, Any]) -> str:
        raw = detail.get("player") or ""
        if raw:
            return self._players.get(raw, raw)
        meta = detail.get("metadata") or {}
        for key in ("Player", "PlayerId", "Winner", "FoulerPlayer", "Recipient"):
            val = _deep_find_value(meta, [key])
            if val:
                return self._players.get(val, val)
        return "-"

    async def publish(self, source: str, detail_type: str, detail: dict[str, Any]) -> None:
        minute = detail.get("minute", 0)
        second = detail.get("second", 0)
        event_type = str(detail.get("event_type", "?"))
        event_id = str(detail.get("event_id", ""))
        team = self._resolve_team(detail)
        player = self._resolve_player(detail)
        kpi_str = _fmt_kpi(event_id, event_type, self._kpis)
        label = _ICONS.get(event_type, f"{event_type:<8}")
        print(f"[{minute:02d}:{second:02d}] {label}  {team:<5} | {player:<22}{kpi_str}")


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


_EVENT_TYPE_MAP: dict[str, str] = {
    "TACKLINGGAME": "FOUL",
    "KICKOFF": "KICK_OFF",
    "GOALKICK": "GOAL_KICK",
    "THROWIN": "THROW_IN",
    "FREEKICK": "FREE_KICK",
    "CROSS": "CROSS",
    "PASS": "PASS",
    "SHOTATGOAL": "SHOT",
    "GOAL": "GOAL",
    "CORNERKICK": "CORNER_KICK",
    "FOUL": "FOUL",
    "CAUTION": "YELLOW",
    "YELLOW": "YELLOW",
    "RED": "RED",
    "SUBSTITUTION": "SUB",
    "OTHERBALLACTION": "OTHER_BALL_ACTION",
    "KICK_OFF": "KICK_OFF",
    "FINALWHISTLE": "FINAL_WHISTLE",
    "ADDITIONALTIMEDISPLAYED": "OTHER",
}


_VALID_EVENT_TYPES: set[str] = {
    "PASS",
    "SHOT",
    "GOAL",
    "CORNER_KICK",
    "FOUL",
    "YELLOW",
    "RED",
    "SUB",
    "THROW_IN",
    "GOAL_KICK",
    "FREE_KICK",
    "TACKLING_GAME",
    "FINAL_WHISTLE",
    "KICK_OFF",
    "OTHER_BALL_ACTION",
    "EVENT",
    "OTHER",
    "PLAY",
    "CROSS",
}


def _normalize_json_event_type(raw_type: str) -> str:
    event_type = raw_type.strip().upper()
    if event_type in _VALID_EVENT_TYPES:
        return event_type
    return _EVENT_TYPE_MAP.get(event_type, "OTHER")


def _load_events_from_json(path: str) -> list[Any]:
    """Load events from a pre-converted JSON file."""
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)  # type: ignore[no-any-return]


async def _run(speed: int, events_path: str | None) -> int:
    """Run the replay engine and return exit code."""
    from src.domain.entities import MatchEvent

    # Load events — JSON preferred (richer), XML as fallback
    resolved_path = Path(events_path) if events_path else (
        _DEFAULT_EVENTS_JSON if _DEFAULT_EVENTS_JSON.exists() else None
    )

    if resolved_path is not None:
        print(f"Loading events from JSON: {resolved_path}")
        try:
            raw = _load_events_from_json(str(resolved_path))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

        # Compute kickoff as the minimum timestamp across all events
        kickoff_dt: datetime | None = None
        for e in raw:
            ts = e.get("timestamp")
            if ts:
                try:
                    dt = _parse_dt(ts)
                    dt = dt if dt.tzinfo else dt.replace(tzinfo=UTC)
                    if kickoff_dt is None or dt < kickoff_dt:
                        kickoff_dt = dt
                except (ValueError, OverflowError):
                    pass

        events = []
        for e in raw:
            minute, second = 0, 0
            if kickoff_dt:
                ts = e.get("timestamp")
                if ts:
                    try:
                        dt = _parse_dt(ts)
                        dt = dt if dt.tzinfo else dt.replace(tzinfo=UTC)
                        delta = (dt - kickoff_dt).total_seconds()
                        minute = int(min(120, max(0, delta // 60)))
                        second = int(min(59, max(0, delta % 60)))
                    except (ValueError, OverflowError):
                        pass
            event_type = _normalize_json_event_type(str(e.get("event_type", "")))
            events.append(
                MatchEvent(
                    event_id=e["event_id"],
                    minute=minute,
                    second=second,
                    event_type=event_type,
                    team=e.get("team") or "",
                    player=e.get("player"),
                    x_position=e.get("x_position"),
                    y_position=e.get("y_position"),
                    metadata=e.get("metadata", {}),
                )
            )
        events.sort(key=lambda ev: (ev.minute, ev.second))
    else:
        xml_path = str(_DEFAULT_EVENTS_XML)
        print(f"Parsing events from XML: {xml_path}")
        try:
            events = parse_events(xml_path)
        except (FileNotFoundError, ReplayParseError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1

    goal_count = sum(1 for event in events if event.event_type == "GOAL")

    team_lookup, player_lookup = _load_match_lookups()
    kpi_lookup = _load_kpi_lookup()
    print(
        f"Loaded {len(events)} events  |  speed_factor={speed}  |  "
        f"teams={len(team_lookup)}  players={len(player_lookup)}  kpis={len(kpi_lookup)}"
    )
    print(f"Estimated duration: ~{(events[-1].minute * 60 + events[-1].second) / speed:.1f}s")
    print("-" * 60)

    engine = ReplayEngine(
        events=events,
        publisher=PrintPublisher(team_lookup, player_lookup, kpi_lookup),
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
    print(f"Replay complete ({len(events)} events, {goal_count} goals).")
    return 0


def main() -> None:
    args = _parse_args()
    sys.exit(asyncio.run(_run(args.speed, args.events)))


if __name__ == "__main__":
    main()
