"""Tests for UuidIdGenerator."""

import pytest

from src.infrastructure.id_generator.uuid_id_generator import UuidIdGenerator


@pytest.mark.unit
def test_new_id_returns_string_with_prefix():
    """Test new_id returns a string starting with the prefix."""
    generator = UuidIdGenerator()
    
    result = generator.new_id("ROOM")
    
    assert isinstance(result, str)
    assert result.startswith("ROOM-")


@pytest.mark.unit
def test_new_id_format():
    """Test new_id returns ID in correct format: PREFIX-8chars."""
    generator = UuidIdGenerator()
    
    result = generator.new_id("WIN")
    
    # Should be WIN-xxxxxxxx (8 hex chars)
    parts = result.split("-")
    assert len(parts) == 2
    assert parts[0] == "WIN"
    assert len(parts[1]) == 8
    # Should be hex characters
    assert all(c in "0123456789abcdef" for c in parts[1])


@pytest.mark.unit
def test_new_id_generates_unique_ids():
    """Test new_id generates unique IDs on each call."""
    generator = UuidIdGenerator()
    
    # Generate 100 IDs
    ids = [generator.new_id("TEST") for _ in range(100)]
    
    # All should be unique
    assert len(ids) == len(set(ids))


@pytest.mark.unit
def test_new_id_works_with_different_prefixes():
    """Test new_id works with various prefixes."""
    generator = UuidIdGenerator()
    
    room_id = generator.new_id("ROOM")
    window_id = generator.new_id("WIN")
    pred_id = generator.new_id("PRED")
    
    assert room_id.startswith("ROOM-")
    assert window_id.startswith("WIN-")
    assert pred_id.startswith("PRED-")
    
    # All should be different
    assert room_id != window_id != pred_id


@pytest.mark.unit
def test_new_id_handles_empty_prefix():
    """Test new_id works with empty prefix."""
    generator = UuidIdGenerator()
    
    result = generator.new_id("")
    
    # Should be -xxxxxxxx
    assert result.startswith("-")
    assert len(result) == 9  # - + 8 chars


@pytest.mark.unit
def test_new_id_handles_special_characters_in_prefix():
    """Test new_id works with special characters in prefix."""
    generator = UuidIdGenerator()
    
    result = generator.new_id("MY_PREFIX")
    
    assert result.startswith("MY_PREFIX-")
    assert len(result.split("-")[1]) == 8
