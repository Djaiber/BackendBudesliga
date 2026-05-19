"""UUID-based ID generator implementation."""

import uuid


class UuidIdGenerator:
    """
    ID generator implementation using UUID4.

    Implements the IdGenerator port using Python's uuid.uuid4().
    Generates IDs in the format: PREFIX-uuid (e.g., 'ROOM-abc123...')
    """

    def new_id(self, prefix: str) -> str:
        """
        Generate a new unique ID with the given prefix.

        Args:
            prefix: Prefix for the ID (e.g., 'ROOM', 'WIN', 'PRED')

        Returns:
            Unique ID string like 'ROOM-abc123...'
        """
        return f"{prefix}-{uuid.uuid4().hex[:8]}"
