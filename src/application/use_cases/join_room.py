"""Join room use case."""

from ...domain.entities import Player, Room
from ...domain.ports import (
    Clock,
    IdGenerator,
    RoomRepository,
    ScoreRepository,
    WebSocketBroadcaster,
)
from ...domain.services import MatchmakerService, TierService
from ..dto import JoinRoomResult, player_to_dto


class JoinRoomUseCase:
    """
    Use case for player joining a room.

    Handles:
    - Auto-matching to existing room or creating new room
    - Explicit room join
    - Room merging when needed
    - Broadcasting join events
    """

    def __init__(
        self,
        room_repo: RoomRepository,
        score_repo: ScoreRepository,
        broadcaster: WebSocketBroadcaster,
        id_gen: IdGenerator,
        clock: Clock,
    ) -> None:
        """
        Initialize use case with dependencies.

        Args:
            room_repo: Room repository port
            score_repo: Score repository port
            broadcaster: WebSocket broadcaster port
            id_gen: ID generator port
            clock: Clock port
        """
        self._room_repo = room_repo
        self._score_repo = score_repo
        self._broadcaster = broadcaster
        self._id_gen = id_gen
        self._clock = clock
        self._matchmaker = MatchmakerService()

    async def execute(
        self,
        user_id: str,
        player_name: str,
        connection_id: str,
        room_id: str | None = None,
    ) -> JoinRoomResult:
        """
        Execute join room use case.

        Args:
            user_id: Unique player identifier
            player_name: Player display name
            connection_id: WebSocket connection ID
            room_id: Optional specific room to join (None = auto-match)

        Returns:
            JoinRoomResult with room, player, and merge status
        """
        # Get or create player
        player = await self._score_repo.get_player(user_id)
        if player is None:
            tier_service = TierService()
            tier = tier_service.get_tier(0)
            player = Player(
                user_id=user_id,
                name=player_name,
                score=0,
                tier=tier,
                streak=0,
            )
            await self._score_repo.upsert_player(player)

        # Find or create room
        if room_id is not None:
            # Explicit room join
            room = await self._room_repo.get(room_id)
            if room is None:
                raise ValueError(f"Room {room_id} not found")
            if not self._matchmaker.can_join(room):
                raise ValueError(f"Room {room_id} is full")

            await self._room_repo.add_player(room_id, player)
            room = await self._room_repo.get(room_id)
            assert room is not None

            # Broadcast player joined to room
            await self._broadcaster.broadcast_to_room(
                room_id=room_id,
                message={
                    "type": "player_joined",
                    "player": player_to_dto(player),
                },
            )

            # Send room joined to player
            await self._broadcaster.send_to_connection(
                connection_id=connection_id,
                message={
                    "type": "room_joined",
                    "room_id": room_id,
                    "player": player_to_dto(player),
                    "players": [player_to_dto(p) for p in room.players],
                },
            )

            return JoinRoomResult(room=room, player=player, was_merged=False)

        # Auto-match: find mergeable room or create new
        active_rooms = await self._room_repo.list_by_status("active")
        mergeable_rooms = [r for r in active_rooms if r.is_mergeable()]

        if mergeable_rooms:
            # Join first mergeable room
            target_room = mergeable_rooms[0]
            await self._room_repo.add_player(target_room.room_id, player)
            room = await self._room_repo.get(target_room.room_id)
            assert room is not None

            # Broadcast player joined
            await self._broadcaster.broadcast_to_room(
                room_id=target_room.room_id,
                message={
                    "type": "player_joined",
                    "player": player_to_dto(player),
                },
            )

            # Send room joined to player
            await self._broadcaster.send_to_connection(
                connection_id=connection_id,
                message={
                    "type": "room_joined",
                    "room_id": target_room.room_id,
                    "player": player_to_dto(player),
                    "players": [player_to_dto(p) for p in room.players],
                },
            )

            return JoinRoomResult(room=room, player=player, was_merged=False)

        # Create new room
        new_room_id = self._id_gen.new_id("ROOM")
        new_room = Room(
            room_id=new_room_id,
            players=(player,),
            status="active",
            created_at=self._clock.now_ms(),
        )
        await self._room_repo.save(new_room)

        # Send room joined to player
        await self._broadcaster.send_to_connection(
            connection_id=connection_id,
            message={
                "type": "room_joined",
                "room_id": new_room_id,
                "player": player_to_dto(player),
                "players": [player_to_dto(player)],
            },
        )

        return JoinRoomResult(room=new_room, player=player, was_merged=False)
