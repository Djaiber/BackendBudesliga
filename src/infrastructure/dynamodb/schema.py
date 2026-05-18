"""
DynamoDB single-table schema key builders.

Table structure:
- Primary key: PK (S), SK (S)
- GSI1: GSI1_PK (S), GSI1_SK (N), all attributes projected
- TTL attribute: expires_at (N) - used on connection items

Entity patterns:
- Room metadata: PK=ROOM#<id>, SK=METADATA
- Room players: PK=ROOM#<id>, SK=PLAYER#<user_id>
- User profile: PK=USER#<user_id>, SK=PROFILE
- Connection: PK=CONN#<conn_id>, SK=METADATA
- Window metadata: PK=WINDOW#<id>, SK=METADATA
- Window submission: PK=WINDOW#<id>, SK=SUBMISSION#<user_id>
- Prompt cache: PK=CACHE#PROMPT, SK=<cache_key>

GSI1 patterns:
- Active rooms: GSI1_PK=STATUS#active, GSI1_SK=<created_at_ms>
- Room connections: GSI1_PK=ROOM#<room_id>, GSI1_SK=<created_at_ms>
"""


# ============================================================================
# ROOM KEYS
# ============================================================================


def room_pk(room_id: str) -> str:
    """
    Build primary key for room partition.

    Args:
        room_id: Room identifier

    Returns:
        PK value like 'ROOM#abc123'
    """
    return f"ROOM#{room_id}"


def room_meta_sk() -> str:
    """
    Build sort key for room metadata item.

    Returns:
        SK value 'METADATA'
    """
    return "METADATA"


def player_sk(user_id: str) -> str:
    """
    Build sort key for player in room.

    Args:
        user_id: User identifier

    Returns:
        SK value like 'PLAYER#user123'
    """
    return f"PLAYER#{user_id}"


# ============================================================================
# USER KEYS
# ============================================================================


def user_pk(user_id: str) -> str:
    """
    Build primary key for user partition.

    Args:
        user_id: User identifier

    Returns:
        PK value like 'USER#user123'
    """
    return f"USER#{user_id}"


def user_profile_sk() -> str:
    """
    Build sort key for user profile item.

    Returns:
        SK value 'PROFILE'
    """
    return "PROFILE"


# ============================================================================
# CONNECTION KEYS
# ============================================================================


def conn_pk(conn_id: str) -> str:
    """
    Build primary key for WebSocket connection.

    Args:
        conn_id: Connection identifier

    Returns:
        PK value like 'CONN#abc123'
    """
    return f"CONN#{conn_id}"


def conn_meta_sk() -> str:
    """
    Build sort key for connection metadata.

    Returns:
        SK value 'METADATA'
    """
    return "METADATA"


# ============================================================================
# WINDOW KEYS
# ============================================================================


def window_pk(window_id: str) -> str:
    """
    Build primary key for prediction window partition.

    Args:
        window_id: Window identifier

    Returns:
        PK value like 'WINDOW#win123'
    """
    return f"WINDOW#{window_id}"


def window_meta_sk() -> str:
    """
    Build sort key for window metadata item.

    Returns:
        SK value 'METADATA'
    """
    return "METADATA"


def submission_sk(user_id: str) -> str:
    """
    Build sort key for prediction submission.

    Args:
        user_id: User identifier

    Returns:
        SK value like 'SUBMISSION#user123'
    """
    return f"SUBMISSION#{user_id}"


# ============================================================================
# CACHE KEYS
# ============================================================================


def cache_pk() -> str:
    """
    Build primary key for cache partition.

    Returns:
        PK value 'CACHE#PROMPT'
    """
    return "CACHE#PROMPT"


def cache_sk(cache_key: str) -> str:
    """
    Build sort key for cached item.

    Args:
        cache_key: Cache key (hash of game + events)

    Returns:
        SK value (the cache key itself)
    """
    return cache_key


# ============================================================================
# GSI1 KEYS (for queries)
# ============================================================================


def gsi1_status_pk(status: str) -> str:
    """
    Build GSI1 primary key for status-based queries.

    Used for finding rooms by status (active, inactive, etc.).

    Args:
        status: Room status

    Returns:
        GSI1_PK value like 'STATUS#active'
    """
    return f"STATUS#{status}"


def gsi1_room_pk(room_id: str) -> str:
    """
    Build GSI1 primary key for room-based queries.

    Used for finding connections by room.

    Args:
        room_id: Room identifier

    Returns:
        GSI1_PK value like 'ROOM#abc123'
    """
    return f"ROOM#{room_id}"
