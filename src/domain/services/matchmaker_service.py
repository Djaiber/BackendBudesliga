"""Matchmaker service for managing room capacity and merging."""

from src.domain.entities import Room


class MatchmakerService:
    """
    Service for room matchmaking and merging logic.

    Rules:
    - Rooms must have 3-4 players to be viable
    - Rooms with <3 players should be merged
    - Merged rooms cannot exceed 4 players
    """

    MIN_PLAYERS = 3
    MAX_PLAYERS = 4

    def find_merge_candidates(self, rooms: list[Room]) -> list[tuple[Room, Room]]:
        """
        Find pairs of rooms that should be merged.

        Args:
            rooms: List of rooms to evaluate

        Returns:
            List of room pairs to merge. Each room appears at most once.
        """
        # Filter to mergeable rooms (< MIN_PLAYERS and active)
        mergeable = [r for r in rooms if r.is_mergeable()]

        pairs: list[tuple[Room, Room]] = []
        used_room_ids: set[str] = set()

        # Try to pair rooms
        for i, room1 in enumerate(mergeable):
            if room1.room_id in used_room_ids:
                continue

            for room2 in mergeable[i + 1 :]:
                if room2.room_id in used_room_ids:
                    continue

                # Check if combined size is valid
                combined_size = len(room1.players) + len(room2.players)
                if combined_size <= self.MAX_PLAYERS:
                    pairs.append((room1, room2))
                    used_room_ids.add(room1.room_id)
                    used_room_ids.add(room2.room_id)
                    break

        return pairs

    def can_join(self, room: Room) -> bool:
        """
        Check if a player can join a room.

        Args:
            room: Room to check

        Returns:
            True if room is active and not full
        """
        return room.status == Room.ACTIVE and len(room.players) < self.MAX_PLAYERS
