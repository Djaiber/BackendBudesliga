"""Tests for DynamoDB schema key builders."""

from src.infrastructure.dynamodb import schema


def test_room_pk() -> None:
    """Test room primary key builder."""
    assert schema.room_pk("abc123") == "ROOM#abc123"
    assert schema.room_pk("test-room-1") == "ROOM#test-room-1"


def test_room_meta_sk() -> None:
    """Test room metadata sort key builder."""
    assert schema.room_meta_sk() == "METADATA"


def test_player_sk() -> None:
    """Test player sort key builder."""
    assert schema.player_sk("user123") == "PLAYER#user123"
    assert schema.player_sk("alice") == "PLAYER#alice"


def test_user_pk() -> None:
    """Test user primary key builder."""
    assert schema.user_pk("user123") == "USER#user123"
    assert schema.user_pk("bob") == "USER#bob"


def test_user_profile_sk() -> None:
    """Test user profile sort key builder."""
    assert schema.user_profile_sk() == "PROFILE"


def test_conn_pk() -> None:
    """Test connection primary key builder."""
    assert schema.conn_pk("conn123") == "CONN#conn123"
    assert schema.conn_pk("abc-def-ghi") == "CONN#abc-def-ghi"


def test_conn_meta_sk() -> None:
    """Test connection metadata sort key builder."""
    assert schema.conn_meta_sk() == "METADATA"


def test_window_pk() -> None:
    """Test window primary key builder."""
    assert schema.window_pk("win123") == "WINDOW#win123"
    assert schema.window_pk("prediction-1") == "WINDOW#prediction-1"


def test_window_meta_sk() -> None:
    """Test window metadata sort key builder."""
    assert schema.window_meta_sk() == "METADATA"


def test_submission_sk() -> None:
    """Test submission sort key builder."""
    assert schema.submission_sk("user123") == "SUBMISSION#user123"
    assert schema.submission_sk("alice") == "SUBMISSION#alice"


def test_cache_pk() -> None:
    """Test cache primary key builder."""
    assert schema.cache_pk() == "CACHE#PROMPT"


def test_cache_sk() -> None:
    """Test cache sort key builder."""
    assert schema.cache_sk("abc123") == "abc123"
    assert schema.cache_sk("hash-of-game-and-events") == "hash-of-game-and-events"


def test_gsi1_status_pk() -> None:
    """Test GSI1 status primary key builder."""
    assert schema.gsi1_status_pk("active") == "STATUS#active"
    assert schema.gsi1_status_pk("inactive") == "STATUS#inactive"


def test_gsi1_room_pk() -> None:
    """Test GSI1 room primary key builder."""
    assert schema.gsi1_room_pk("room123") == "ROOM#room123"
    assert schema.gsi1_room_pk("test-room") == "ROOM#test-room"


def test_key_uniqueness() -> None:
    """Test that different entity types have unique key patterns."""
    # Ensure no collisions between entity types
    room_id = "123"
    user_id = "123"
    conn_id = "123"
    window_id = "123"
    
    keys = {
        schema.room_pk(room_id),
        schema.user_pk(user_id),
        schema.conn_pk(conn_id),
        schema.window_pk(window_id),
        schema.cache_pk(),
    }
    
    # All keys should be unique
    assert len(keys) == 5


def test_sort_key_uniqueness() -> None:
    """Test that different sort key types within same partition are unique."""
    user_id = "user123"
    
    # Within a room partition
    room_sort_keys = {
        schema.room_meta_sk(),
        schema.player_sk(user_id),
        schema.player_sk("user456"),
    }
    assert len(room_sort_keys) == 3
    
    # Within a window partition
    window_sort_keys = {
        schema.window_meta_sk(),
        schema.submission_sk(user_id),
        schema.submission_sk("user456"),
    }
    assert len(window_sort_keys) == 3
    
    # METADATA is reused across partitions (which is fine - different PKs)
    assert schema.room_meta_sk() == schema.conn_meta_sk() == schema.window_meta_sk()


def test_gsi1_key_patterns() -> None:
    """Test GSI1 key patterns for queries."""
    # Status-based queries
    assert schema.gsi1_status_pk("active").startswith("STATUS#")
    
    # Room-based queries
    assert schema.gsi1_room_pk("room123").startswith("ROOM#")
    
    # Different patterns
    assert schema.gsi1_status_pk("active") != schema.gsi1_room_pk("active")
