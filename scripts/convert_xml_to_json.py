#!/usr/bin/env python3
"""
Convert XML match data to normalized JSON format for replay engine.

Reads:
- DataExploration/datos/Events_Anonym.xml
- DataExploration/datos/MatchInformations_Anonym.xml
- DataExploration/datos/kpi_data_Bayern_Hamburg.xml

Outputs to scripts/output/:
- events.json (sorted by minute, second)
- match_info.json (teams, lineups, metadata)
- kpi.json (KPI snapshots indexed by minute)
"""

import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

# Base directories
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "DataExploration" / "datos"
OUTPUT_DIR = SCRIPT_DIR / "output"


@dataclass
class MatchEvent:
    """Normalized match event."""

    event_id: str
    minute: int
    second: int
    event_type: str
    team: str | None
    player: str | None
    x_position: float | None
    y_position: float | None
    timestamp: str
    metadata: dict[str, Any]


@dataclass
class Player:
    """Player information."""

    player_id: str
    shirt_number: int
    first_name: str
    last_name: str
    short_name: str
    position: str
    starting: bool
    team_leader: bool


@dataclass
class Team:
    """Team information."""

    team_id: str
    team_name: str
    short_name: str
    three_letter_code: str
    role: str  # home or guest
    lineup: str
    players: list[Player]


@dataclass
class MatchInfo:
    """Match metadata."""

    match_id: str
    competition: str
    season: str
    match_day: int
    kickoff_time: str
    home_team: Team
    guest_team: Team
    final_score: str
    stadium: str
    pitch_dimensions: dict[str, float]


def parse_match_time(match_time_str: str | None) -> tuple[int, int]:
    """
    Parse MatchTime attribute to (minute, second).

    Examples:
    - "00:45:23" -> (45, 23)
    - "01:32:15" -> (92, 15)  # second half
    - None -> (0, 0)
    """
    if not match_time_str:
        return (0, 0)

    parts = match_time_str.split(":")
    if len(parts) != 3:
        return (0, 0)

    try:
        half = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2])

        # Convert to absolute match minute
        if half == 1:
            return (minute, second)
        else:  # half == 2
            return (45 + minute, second)
    except (ValueError, IndexError):
        return (0, 0)


def normalize_event_type(elem: ET.Element) -> str:
    """
    Extract and normalize event type from XML element.

    Priority:
    1. Child element tag (Play, ShotAtGoal, GoalKick, etc.)
    2. Element tag itself
    """
    # Check for child elements first
    for child in elem:
        tag = child.tag
        if tag in [
            "Play",
            "ShotAtGoal",
            "GoalKick",
            "CornerKick",
            "ThrowIn",
            "FreeKick",
            "TacklingGame",
            "Foul",
            "Caution",
            "Goal",
            "OtherBallAction",
            "Delete",
            "FinalWhistle",
            "AdditionalTimeDisplayed",
        ]:
            # For Play, check if it's a Pass or Cross
            if tag == "Play":
                for subchild in child:
                    if subchild.tag in ["Pass", "Cross"]:
                        return subchild.tag.upper()
                return "PLAY"

            # For ShotAtGoal, check outcome
            if tag == "ShotAtGoal":
                for subchild in child:
                    if subchild.tag in ["Goal", "ShotWide", "BlockedShot", "ShotSaved"]:
                        if subchild.tag == "Goal":
                            return "GOAL"
                        return "SHOT"
                return "SHOT"

            return tag.upper()

    # Fallback to element tag
    return elem.tag.upper()


def extract_event_metadata(elem: ET.Element) -> dict[str, Any]:
    """Extract all relevant metadata from event element."""
    metadata: dict[str, Any] = {}

    # Element attributes
    for key, value in elem.attrib.items():
        if key not in ["EventId", "MatchId", "EventTime", "X-Position", "Y-Position"]:
            metadata[key] = value

    # Child element attributes
    for child in elem:
        child_data: dict[str, Any] = dict(child.attrib)
        if child_data:
            metadata[child.tag] = child_data

    return metadata


def parse_events_xml(xml_path: Path) -> list[MatchEvent]:
    """Parse Events_Anonym.xml and return normalized events."""
    print(f"Parsing events from {xml_path}...")

    events: list[MatchEvent] = []

    try:
        # Read file and skip any comment lines at the beginning
        with open(xml_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Remove leading comment lines
            lines = content.split("\n")
            xml_start = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("<?xml") or line.strip().startswith("<"):
                    if not line.strip().startswith("<!--"):
                        xml_start = i
                        break
            content = "\n".join(lines[xml_start:])

        # Parse from string
        from io import StringIO

        xml_file = StringIO(content)
        context = ET.iterparse(xml_file, events=("end",))

        for event_type, elem in context:
            if elem.tag != "Event":
                continue

            event_id = elem.get("EventId", "")
            timestamp = elem.get("EventTime", "")
            x_pos = elem.get("X-Position")
            y_pos = elem.get("Y-Position")

            # Parse match time
            match_time = elem.get("MatchTime")
            minute, second = parse_match_time(match_time)

            # Extract team and player
            team = None
            player = None

            # Check element attributes first
            team = elem.get("Team")
            player = elem.get("Player")

            # Check child elements
            if not team or not player:
                for child in elem:
                    if not team:
                        team = child.get("Team")
                    if not player:
                        player = child.get("Player")
                    if team and player:
                        break

            # Normalize event type
            event_type_str = normalize_event_type(elem)

            # Skip Delete events
            if event_type_str == "DELETE":
                elem.clear()
                continue

            # Extract metadata
            metadata = extract_event_metadata(elem)

            events.append(
                MatchEvent(
                    event_id=event_id,
                    minute=minute,
                    second=second,
                    event_type=event_type_str,
                    team=team,
                    player=player,
                    x_position=float(x_pos) if x_pos else None,
                    y_position=float(y_pos) if y_pos else None,
                    timestamp=timestamp,
                    metadata=metadata,
                )
            )

            # Clear element to free memory
            elem.clear()

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        return []

    # Sort by minute, then second
    events.sort(key=lambda e: (e.minute, e.second))

    print(f"Parsed {len(events)} events")
    return events


def parse_match_info_xml(xml_path: Path) -> MatchInfo | None:
    """Parse MatchInformations_Anonym.xml and return match metadata."""
    print(f"Parsing match info from {xml_path}...")

    try:
        tree = ET.parse(str(xml_path))
        root = tree.getroot()

        match_info_elem = root.find(".//MatchInformation")
        if match_info_elem is None:
            print("No MatchInformation element found", file=sys.stderr)
            return None

        general = match_info_elem.find("General")
        if general is None:
            print("No General element found", file=sys.stderr)
            return None

        environment = match_info_elem.find("Environment")
        teams_elem = match_info_elem.find("Teams")

        # Parse teams
        home_team = None
        guest_team = None

        if teams_elem is not None:
            for team_elem in teams_elem.findall("Team"):
                role = team_elem.get("Role", "").lower()
                players: list[Player] = []

                players_elem = team_elem.find("Players")
                if players_elem is not None:
                    for player_elem in players_elem.findall("Player"):
                        players.append(
                            Player(
                                player_id=player_elem.get("PersonId", ""),
                                shirt_number=int(player_elem.get("ShirtNumber", "0")),
                                first_name=player_elem.get("FirstName", ""),
                                last_name=player_elem.get("LastName", ""),
                                short_name=player_elem.get("Shortname", ""),
                                position=player_elem.get("PlayingPosition", ""),
                                starting=player_elem.get("Starting", "").lower() == "true",
                                team_leader=player_elem.get("TeamLeader", "").lower()
                                == "true",
                            )
                        )

                team = Team(
                    team_id=team_elem.get("TeamId", ""),
                    team_name=team_elem.get("TeamName", ""),
                    short_name=team_elem.get("ShortName", ""),
                    three_letter_code=team_elem.get("ThreeLetterCode", ""),
                    role=role,
                    lineup=team_elem.get("LineUp", ""),
                    players=players,
                )

                if role == "home":
                    home_team = team
                elif role == "guest":
                    guest_team = team

        if not home_team or not guest_team:
            print("Could not parse both teams", file=sys.stderr)
            return None

        match_info = MatchInfo(
            match_id=general.get("MatchId", ""),
            competition=general.get("CompetitionName", ""),
            season=general.get("Season", ""),
            match_day=int(general.get("MatchDay", "0")),
            kickoff_time=general.get("KickoffTime", ""),
            home_team=home_team,
            guest_team=guest_team,
            final_score=general.get("Result", ""),
            stadium=environment.get("StadiumName", "") if environment is not None else "",
            pitch_dimensions={
                "x": float(environment.get("PitchX", "105.0"))
                if environment is not None
                else 105.0,
                "y": float(environment.get("PitchY", "68.0"))
                if environment is not None
                else 68.0,
            },
        )

        print(f"Parsed match info: {match_info.home_team.team_name} vs {match_info.guest_team.team_name}")
        return match_info

    except (ET.ParseError, ValueError) as e:
        print(f"Error parsing match info XML: {e}", file=sys.stderr)
        return None


def parse_kpi_xml(xml_path: Path) -> dict[int, dict[str, Any]]:
    """Parse kpi_data_Bayern_Hamburg.xml and return KPI snapshots by minute."""
    print(f"Parsing KPI data from {xml_path}...")

    kpi_data: dict[int, dict[str, Any]] = {}

    try:
        # Read file and skip any comment lines at the beginning
        with open(xml_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Remove leading comment lines
            lines = content.split("\n")
            xml_start = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("<?xml") or line.strip().startswith("<"):
                    if not line.strip().startswith("<!--"):
                        xml_start = i
                        break
            content = "\n".join(lines[xml_start:])

        from io import StringIO

        xml_file = StringIO(content)
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Find all KPI elements (structure may vary)
        for elem in root.iter():
            # Look for elements with minute/time attributes
            minute_str = elem.get("Minute") or elem.get("minute") or elem.get("Time")
            if minute_str:
                try:
                    minute = int(minute_str)
                    if minute not in kpi_data:
                        kpi_data[minute] = {}

                    # Store all attributes for this minute
                    for key, value in elem.attrib.items():
                        if key.lower() not in ["minute", "time"]:
                            kpi_data[minute][key] = value

                except ValueError:
                    continue

        print(f"Parsed KPI data for {len(kpi_data)} minutes")
        return kpi_data

    except ET.ParseError as e:
        print(f"Error parsing KPI XML: {e}", file=sys.stderr)
        return {}


def main() -> int:
    """Main conversion function."""
    print("=" * 60)
    print("XML to JSON Converter for Connected Arena")
    print("=" * 60)

    # Check input files
    events_xml = DATA_DIR / "Events_Anonym.xml"
    match_info_xml = DATA_DIR / "MatchInformations_Anonym.xml"
    kpi_xml = DATA_DIR / "kpi_data_Bayern_Hamburg.xml"

    missing_files = []
    for file_path in [events_xml, match_info_xml, kpi_xml]:
        if not file_path.exists():
            missing_files.append(str(file_path))

    if missing_files:
        print("\nERROR: Missing input files:", file=sys.stderr)
        for file_path in missing_files:
            print(f"  - {file_path}", file=sys.stderr)
        return 1

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Parse events
    events = parse_events_xml(events_xml)
    if not events:
        print("ERROR: No events parsed", file=sys.stderr)
        return 1

    # Parse match info
    match_info = parse_match_info_xml(match_info_xml)
    if not match_info:
        print("ERROR: Could not parse match info", file=sys.stderr)
        return 1

    # Parse KPI data
    kpi_data = parse_kpi_xml(kpi_xml)

    # Write output files
    print("\nWriting output files...")

    events_output = OUTPUT_DIR / "events.json"
    with open(events_output, "w", encoding="utf-8") as f:
        json.dump([asdict(e) for e in events], f, indent=2, ensure_ascii=False)
    print(f"  ✓ {events_output} ({len(events)} events)")

    match_info_output = OUTPUT_DIR / "match_info.json"
    with open(match_info_output, "w", encoding="utf-8") as f:
        json.dump(asdict(match_info), f, indent=2, ensure_ascii=False)
    print(f"  ✓ {match_info_output}")

    kpi_output = OUTPUT_DIR / "kpi.json"
    with open(kpi_output, "w", encoding="utf-8") as f:
        json.dump(kpi_data, f, indent=2, ensure_ascii=False)
    print(f"  ✓ {kpi_output} ({len(kpi_data)} minute snapshots)")

    print("\n" + "=" * 60)
    print("Conversion complete!")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
