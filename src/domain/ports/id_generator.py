"""ID generator port - abstract interface for generating unique IDs."""

from typing import Protocol


class IdGenerator(Protocol):
    """
    Abstract ID generator for creating unique identifiers.

    Allows use cases to generate IDs without directly calling uuid.uuid4(),
    making them deterministic and testable.
    """

    def new_id(self, prefix: str) -> str:
        """
        Generate a new unique ID with the given prefix.

        Args:
            prefix: Prefix for the ID (e.g., 'ROOM', 'WIN', 'PRED')

        Returns:
            Unique ID string like 'ROOM-abc123' or 'WIN-def456'
        """
        ...
