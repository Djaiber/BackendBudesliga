"""DynamoDB implementation of ScoreRepository port."""

import logging
from typing import Any

import aioboto3

from src.domain.entities import Player, ScoreDelta
from src.infrastructure.dynamodb import schema
from src.infrastructure.dynamodb.client import get_ddb_resource_kwargs

logger = logging.getLogger(__name__)


class ScoreRepositoryDDB:
    """
    DynamoDB adapter for ScoreRepository port.

    Item structure:
    - User profile: PK=USER#<user_id>, SK=PROFILE, name, score, tier, streak
    - Room membership: PK=USER#<user_id>, SK=ROOM#<room_id>, GSI1_PK=ROOM#<room_id>, GSI1_SK=<score>

    Uses single-table design with GSI1 for leaderboard queries (room-based, sorted by score).
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

    async def get_player(self, user_id: str) -> Player | None:
        """Get player by user ID."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            response = await table.get_item(
                Key={
                    "PK": schema.user_pk(user_id),
                    "SK": schema.user_profile_sk(),
                }
            )

            item = response.get("Item")
            if not item:
                return None

            return self._item_to_player(item)

    async def upsert_player(self, player: Player) -> None:
        """Insert or update a player."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            await table.put_item(
                Item={
                    "PK": schema.user_pk(player.user_id),
                    "SK": schema.user_profile_sk(),
                    "user_id": player.user_id,
                    "name": player.name,
                    "score": player.score,
                    "tier": player.tier,
                    "streak": player.streak,
                }
            )

    async def apply_delta(self, delta: ScoreDelta) -> Player:
        """
        Apply a score delta to a player atomically using UpdateItem.

        This ensures concurrent updates don't overwrite each other.
        """
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Use UpdateItem with SET expressions for atomic update
            response = await table.update_item(
                Key={
                    "PK": schema.user_pk(delta.user_id),
                    "SK": schema.user_profile_sk(),
                },
                UpdateExpression="SET score = :score, streak = :streak, tier = :tier",
                ExpressionAttributeValues={
                    ":score": delta.new_score,
                    ":streak": delta.new_streak,
                    ":tier": delta.new_tier,
                },
                ConditionExpression="attribute_exists(PK)",  # Ensure player exists
                ReturnValues="ALL_NEW",
            )

            item = response["Attributes"]
            return self._item_to_player(item)

    async def leaderboard(self, room_id: str) -> list[Player]:
        """
        Get leaderboard for a room using GSI1.

        GSI1_PK = ROOM#<room_id>, GSI1_SK = <score> (numeric)
        Query in descending order to get highest scores first.
        """
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Query GSI1 for room membership items
            response = await table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1_PK = :gsi1_pk",
                ExpressionAttributeValues={":gsi1_pk": schema.gsi1_room_pk(room_id)},
                ScanIndexForward=False,  # Descending order (highest score first)
            )

            # Extract user_ids from room membership items
            user_ids = []
            for item in response.get("Items", []):
                if "user_id" in item:
                    user_ids.append(item["user_id"])

            # Fetch each player's profile
            players = []
            for user_id in user_ids:
                player = await self.get_player(user_id)
                if player:
                    players.append(player)

            # Sort by score descending (in case GSI1_SK wasn't perfectly maintained)
            players.sort(key=lambda p: p.score, reverse=True)

            return players

    def _item_to_player(self, item: dict[str, Any]) -> Player:
        """Convert DynamoDB item to Player entity."""
        return Player(
            user_id=item["user_id"],
            name=item["name"],
            score=int(item["score"]),
            tier=item["tier"],
            streak=int(item["streak"]),
        )
