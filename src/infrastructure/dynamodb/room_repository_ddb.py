"""DynamoDB implementation of RoomRepository port."""

import logging
from typing import Any

import aioboto3

from src.domain.entities import Player, Room
from src.infrastructure.dynamodb import schema
from src.infrastructure.dynamodb.client import get_ddb_resource_kwargs

logger = logging.getLogger(__name__)


class RoomRepositoryDDB:
    """
    DynamoDB adapter for RoomRepository port.

    Item structure:
    - Room metadata: PK=ROOM#<id>, SK=METADATA, status, created_at, GSI1_PK, GSI1_SK
    - Player in room: PK=ROOM#<id>, SK=PLAYER#<user_id>, denormalized Player fields

    Uses single-table design with GSI1 for status-based queries.
    """

    def __init__(
        self,
        table_name: str,
        region: str,
        endpoint_url: str | None = None,
    ) -> None:
        """
        Initialize repository.

        Args:
            table_name: DynamoDB table name
            region: AWS region
            endpoint_url: Optional endpoint override for localstack
        """
        self._table_name = table_name
        self._session = aioboto3.Session()
        self._resource_kwargs = get_ddb_resource_kwargs(region, endpoint_url)

    async def get(self, room_id: str) -> Room | None:
        """Get room by ID, hydrating metadata and all players."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Query entire partition
            response = await table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": schema.room_pk(room_id)},
            )

            items = response.get("Items", [])
            if not items:
                return None

            # Separate metadata and players
            metadata = None
            players = []

            for item in items:
                if item["SK"] == schema.room_meta_sk():
                    metadata = item
                elif item["SK"].startswith("PLAYER#"):
                    players.append(self._item_to_player(item))

            if metadata is None:
                return None

            return Room(
                room_id=room_id,
                players=tuple(players),
                status=metadata["status"],
                created_at=metadata["created_at"],
            )

    async def save(self, room: Room) -> None:
        """Save room metadata and all players using BatchWriteItem."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Build metadata item
            metadata_item = {
                "PK": schema.room_pk(room.room_id),
                "SK": schema.room_meta_sk(),
                "status": room.status,
                "created_at": room.created_at,
                "GSI1_PK": schema.gsi1_status_pk(room.status),
                "GSI1_SK": room.created_at,
            }

            # Build player items
            player_items = [
                {
                    "PK": schema.room_pk(room.room_id),
                    "SK": schema.player_sk(player.user_id),
                    "user_id": player.user_id,
                    "name": player.name,
                    "score": player.score,
                    "tier": player.tier,
                    "streak": player.streak,
                }
                for player in room.players
            ]

            # Write all items
            # First, delete existing players (query + batch delete)
            existing_response = await table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk": schema.room_pk(room.room_id),
                    ":sk_prefix": "PLAYER#",
                },
            )

            # Delete old players
            async with table.batch_writer() as batch:
                for item in existing_response.get("Items", []):
                    await batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

            # Write new state
            async with table.batch_writer() as batch:
                await batch.put_item(Item=metadata_item)
                for player_item in player_items:
                    await batch.put_item(Item=player_item)

    async def list_by_status(self, status: str) -> list[Room]:
        """List rooms by status using GSI1, sorted by created_at."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Query GSI1
            response = await table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1_PK = :gsi1_pk",
                ExpressionAttributeValues={":gsi1_pk": schema.gsi1_status_pk(status)},
                ScanIndexForward=True,  # Sort by GSI1_SK (created_at) ascending
            )

            # Extract room IDs from metadata items
            room_ids = []
            for item in response.get("Items", []):
                if item["SK"] == schema.room_meta_sk():
                    # Extract room_id from PK
                    room_id = item["PK"].replace("ROOM#", "")
                    room_ids.append(room_id)

            # Hydrate each room
            rooms = []
            for room_id in room_ids:
                room = await self.get(room_id)
                if room:
                    rooms.append(room)

            return rooms

    async def add_player(self, room_id: str, player: Player) -> Room:
        """Add player to room, then re-read and return updated room."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Put player item
            await table.put_item(
                Item={
                    "PK": schema.room_pk(room_id),
                    "SK": schema.player_sk(player.user_id),
                    "user_id": player.user_id,
                    "name": player.name,
                    "score": player.score,
                    "tier": player.tier,
                    "streak": player.streak,
                }
            )

            # Re-read room
            room = await self.get(room_id)
            if room is None:
                raise ValueError(f"Room {room_id} not found")

            return room

    async def remove_player(self, room_id: str, user_id: str) -> Room:
        """Remove player from room, then re-read and return updated room."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Delete player item
            await table.delete_item(
                Key={
                    "PK": schema.room_pk(room_id),
                    "SK": schema.player_sk(user_id),
                }
            )

            # Re-read room
            room = await self.get(room_id)
            if room is None:
                raise ValueError(f"Room {room_id} not found")

            return room

    async def delete(self, room_id: str) -> None:
        """Delete entire room partition (metadata + all players)."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Query all items in partition
            response = await table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": schema.room_pk(room_id)},
            )

            # Batch delete all items
            items = response.get("Items", [])
            if items:
                async with table.batch_writer() as batch:
                    for item in items:
                        await batch.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

    def _item_to_player(self, item: dict[str, Any]) -> Player:
        """Convert DynamoDB item to Player entity."""
        return Player(
            user_id=item["user_id"],
            name=item["name"],
            score=int(item["score"]),
            tier=item["tier"],
            streak=int(item["streak"]),
        )
