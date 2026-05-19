"""Pure XML parsing utilities for match replay data.

No I/O beyond reading the file path passed in.  No AWS, no domain logic.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from io import StringIO
from typing import Any
from xml.etree import ElementTree as ET

from dateutil.parser import parse as parse_dt

from src.application.dto.messages import MatchInfo
from src.domain.entities import MatchEvent

logger = logging.getLogger(__name__)

# Raw XML tag (upper-cased) → normalized domain event type
_EVENT_TYPE_MAP: dict[str, str] = {
    "PASS": "PASS",
    "CROSS": "PASS",
    "PLAY": "PASS",
    "SHOTATGOAL": "SHOT",
    "GOAL": "GOAL",
    "CORNERKICK": "CORNER_KICK",
    "FOUL": "FOUL",
    "TACKLINGGAME": "FOUL",
    "CAUTION": "YELLOW",
    "REDCARD": "RED",
}

_OTHER = "OTHER"
_DELETE = "DELETE"


class ReplayParseError(Exception):
    """Raised when XML replay data cannot be parsed."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_events(path: str) -> list[MatchEvent]:
    """Parse Events_Anonym.xml into domain MatchEvent entities.

    Uses EventTime to compute (minute, second) relative to the earliest event
    (kickoff).  Returns events sorted by (minute, second) ascending.
    Skips malformed entries with a warning log; doesn't raise.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise ReplayParseError(f"Cannot read events file '{path}': {exc}") from exc

    content = _strip_leading_comments(content)

    # Collect raw data in first pass
    raw: list[dict[str, Any]] = []
    try:
        for _, elem in ET.iterparse(StringIO(content), events=("end",)):
            if elem.tag != "Event":
                elem.clear()
                continue

            event_type = _normalize_event_type(elem)
            if event_type == _DELETE:
                elem.clear()
                continue

            event_id = elem.get("EventId", "")
            event_time_str = elem.get("EventTime") or ""
            x_str = elem.get("X-Position")
            y_str = elem.get("Y-Position")

            team: str = elem.get("Team") or ""
            player: str | None = elem.get("Player")
            if not team or player is None:
                for child in elem:
                    if not team:
                        team = child.get("Team") or ""
                    if player is None:
                        player = child.get("Player")
                    if team and player is not None:
                        break

            metadata: dict[str, Any] = {
                key: value
                for key, value in elem.attrib.items()
                if key not in ("EventId", "MatchId", "EventTime", "X-Position", "Y-Position")
            }
            for child in elem:
                child_data: dict[str, Any] = dict(child.attrib)
                if child_data:
                    metadata[child.tag] = child_data

            raw.append(
                {
                    "event_id": event_id,
                    "event_time_str": event_time_str,
                    "event_type": event_type,
                    "team": team,
                    "player": player,
                    "x_str": x_str,
                    "y_str": y_str,
                    "metadata": metadata,
                }
            )
            elem.clear()

    except ET.ParseError as exc:
        raise ReplayParseError(f"Malformed XML in '{path}': {exc}") from exc

    if not raw:
        return []

    # Determine kickoff timestamp (earliest EventTime)
    kickoff_dt: datetime | None = None
    for r in raw:
        dt = _parse_event_time(r["event_time_str"])
        if dt is not None and (kickoff_dt is None or dt < kickoff_dt):
            kickoff_dt = dt

    # Build MatchEvent objects with computed (minute, second)
    events: list[MatchEvent] = []
    for r in raw:
        dt = _parse_event_time(r["event_time_str"])
        if dt is not None and kickoff_dt is not None:
            delta_s = (dt - kickoff_dt).total_seconds()
            minute = int(delta_s // 60)
            second = int(delta_s % 60)
            # Cap at valid domain range (0-120 minutes, 0-59 seconds)
            minute = min(120, max(0, minute))
            second = min(59, max(0, second))
        else:
            minute, second = 0, 0

        try:
            events.append(
                MatchEvent(
                    event_id=r["event_id"],
                    minute=minute,
                    second=second,
                    event_type=r["event_type"],
                    team=r["team"],
                    player=r["player"],
                    x_position=float(r["x_str"]) if r["x_str"] else None,
                    y_position=float(r["y_str"]) if r["y_str"] else None,
                    metadata=r["metadata"],
                )
            )
        except (ValueError, TypeError) as exc:
            logger.warning("Skipping malformed event %s: %s", r["event_id"], exc)

    events.sort(key=lambda e: (e.minute, e.second))
    return events


def parse_match_info(path: str) -> MatchInfo:
    """Parse MatchInformations_Anonym.xml into a MatchInfo TypedDict.

    Returns: { 'match_id', 'team_a', 'team_b', 'kickoff_iso', 'lineups' }
    """
    try:
        tree = ET.parse(path)
    except FileNotFoundError:
        raise
    except ET.ParseError as exc:
        raise ReplayParseError(f"Malformed XML in '{path}': {exc}") from exc
    except OSError as exc:
        raise ReplayParseError(f"Cannot read match info file '{path}': {exc}") from exc

    root = tree.getroot()
    match_info_elem = root.find(".//MatchInformation")
    if match_info_elem is None:
        raise ReplayParseError(f"No <MatchInformation> element found in '{path}'")

    general = match_info_elem.find("General")
    if general is None:
        raise ReplayParseError(f"No <General> element found in '{path}'")

    teams_elem = match_info_elem.find("Teams")
    if teams_elem is None:
        raise ReplayParseError(f"No <Teams> element found in '{path}'")

    team_a = ""
    team_b = ""
    lineups: dict[str, list[str]] = {}

    for team_elem in teams_elem.findall("Team"):
        team_name = team_elem.get("TeamName", "")
        role = team_elem.get("Role", "").lower()
        player_names: list[str] = []

        players_elem = team_elem.find("Players")
        if players_elem is not None:
            for p in players_elem.findall("Player"):
                first = p.get("FirstName", "")
                last = p.get("LastName", "")
                name = f"{first} {last}".strip() or p.get("Shortname", "")
                if name:
                    player_names.append(name)

        if role == "home":
            team_a = team_name
        else:
            team_b = team_name
        lineups[team_name] = player_names

    if not team_a or not team_b:
        raise ReplayParseError(f"Could not parse both teams from '{path}'")

    return MatchInfo(
        match_id=general.get("MatchId", ""),
        team_a=team_a,
        team_b=team_b,
        kickoff_iso=general.get("KickoffTime", ""),
        lineups=lineups,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _strip_leading_comments(content: str) -> str:
    """Remove leading comment/BOM lines before the XML declaration."""
    lines = content.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("<?xml") or (
            stripped.startswith("<") and not stripped.startswith("<!--")
        ):
            return "\n".join(lines[i:])
    return content


def _normalize_event_type(elem: ET.Element) -> str:
    """Map raw XML element structure to a normalized domain event type."""
    for child in elem:
        tag = child.tag.upper()

        if tag == "PLAY":
            for subchild in child:
                sub = subchild.tag.upper()
                if sub in ("PASS", "CROSS"):
                    return _EVENT_TYPE_MAP.get(sub, _OTHER)
            return "PASS"

        if tag == "SHOTATGOAL":
            for subchild in child:
                if subchild.tag.upper() == "GOAL":
                    return "GOAL"
            return "SHOT"

        if tag == "DELETE":
            return _DELETE

        normalized = _EVENT_TYPE_MAP.get(tag)
        if normalized:
            return normalized

    return _OTHER


def _parse_event_time(event_time_str: str) -> datetime | None:
    """Parse EventTime ISO string to a timezone-aware datetime; returns None on failure."""
    if not event_time_str:
        return None
    try:
        dt = parse_dt(event_time_str)
        # Ensure timezone-aware for delta computation
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, OverflowError):
        return None
