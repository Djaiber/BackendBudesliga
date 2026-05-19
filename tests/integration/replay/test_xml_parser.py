"""Integration tests for xml_parser — uses the real DataExploration XML files."""

from __future__ import annotations

import os
import tempfile

import pytest

from src.infrastructure.replay.xml_parser import (
    ReplayParseError,
    parse_events,
    parse_match_info,
)

# Path to real data files, resolved relative to project root
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
_DATA_DIR = os.path.join(_PROJECT_ROOT, "DataExploration", "datos")
_EVENTS_XML = os.path.join(_DATA_DIR, "Events_Anonym.xml")
_MATCH_INFO_XML = os.path.join(_DATA_DIR, "MatchInformations_Anonym.xml")

_NORMALIZED_TYPES = {"PASS", "SHOT", "GOAL", "CORNER_KICK", "FOUL", "YELLOW", "RED", "SUB", "OTHER"}

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# parse_events
# ---------------------------------------------------------------------------


def test_parse_events_returns_1635_events() -> None:
    """parse_events on the real Events_Anonym.xml returns exactly 1635 events."""
    events = parse_events(_EVENTS_XML)
    assert len(events) == 1635, f"Expected 1635 events, got {len(events)}"


def test_parse_events_sorted_by_minute_second() -> None:
    """Returned events are sorted ascending by (minute, second)."""
    events = parse_events(_EVENTS_XML)
    times = [(e.minute, e.second) for e in events]
    assert times == sorted(times), "Events are not sorted by (minute, second)"


def test_parse_events_all_types_normalized() -> None:
    """All event_type values fall in the normalized set."""
    events = parse_events(_EVENTS_XML)
    seen_types = {e.event_type for e in events}
    unknown = seen_types - _NORMALIZED_TYPES
    assert not unknown, f"Unexpected event types found: {unknown}"


def test_parse_events_missing_file_raises_file_not_found() -> None:
    """Missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_events("/nonexistent/path/Events_Anonym.xml")


def test_parse_events_malformed_xml_raises_replay_parse_error() -> None:
    """Malformed XML raises ReplayParseError with a clear message."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write("<?xml version='1.0'?><Events><Event EventId='1'</Events>")
        bad_path = f.name

    try:
        with pytest.raises(ReplayParseError, match="Malformed XML"):
            parse_events(bad_path)
    finally:
        os.unlink(bad_path)


# ---------------------------------------------------------------------------
# parse_match_info
# ---------------------------------------------------------------------------


def test_parse_match_info_returns_two_distinct_teams() -> None:
    """parse_match_info returns team_a != team_b, both non-empty."""
    info = parse_match_info(_MATCH_INFO_XML)
    assert info["team_a"], "team_a is empty"
    assert info["team_b"], "team_b is empty"
    assert info["team_a"] != info["team_b"], "team_a == team_b"


def test_parse_match_info_has_all_fields() -> None:
    """MatchInfo has all required keys with non-empty values."""
    info = parse_match_info(_MATCH_INFO_XML)
    assert info["match_id"]
    assert info["kickoff_iso"]
    assert isinstance(info["lineups"], dict)
    assert len(info["lineups"]) == 2


def test_parse_match_info_missing_file_raises_file_not_found() -> None:
    """Missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        parse_match_info("/nonexistent/path/Match.xml")


def test_parse_match_info_malformed_xml_raises_replay_parse_error() -> None:
    """Malformed XML raises ReplayParseError."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write("<?xml version='1.0'?><MatchParameters><broken")
        bad_path = f.name

    try:
        with pytest.raises(ReplayParseError, match="Malformed XML"):
            parse_match_info(bad_path)
    finally:
        os.unlink(bad_path)
