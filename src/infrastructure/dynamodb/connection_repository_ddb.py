"""DynamoDB repository for WebSocket connection tracking."""

import logging
from typing import Any

import aioboto3

from src.infrastructure.dynamodb import schema
from src.infrastructure.dynamodb.client import get_ddb_resource_kwargs

logger = logging.getLogger(__name__)


class ConnectionRepositoryDDB:
    """
    DynamoDB adapter for WebSocket connection tracking.

    This is AWS-specific infrastructure (not a domain port) for managing
    API Gateway WebSocket connections.

    Item structure:
    - Connection: PK=CONN#<conn_id>, SK=METADATA, user_id, room_id, connected_at_ms, ttl
    - GSI1 for room queries: GSI1_PK=ROOM#<room_id>, GSI1_SK=<connected_at_ms>

    TTL: Connections automatically expire after 1 hour (3600 seconds).
    """

    def __init__(
        self,
        table_name: str,
        region: str,
        endpoint_url: str | None = None,
        ttl_seconds: int = 3600,
    ) -> None:
        """
        Initialize repository.

        Args:
            table_name: DynamoDB table name
            region: AWS region
            endpoint_url: Optional endpoint override for localstack
            ttl_seconds: TTL for connections (default 1 hour)
        """
        self._table_name = table_name
        self._session = aioboto3.Session()
        self._resource_kwargs = get_ddb_resource_kwargs(region, endpoint_url)
        self._ttl_seconds = ttl_seconds

    async def put(
        self,
        conn_id: str,
        user_id: str,
        room_id: str,
        connected_at_ms: int,
        user_name: str = "",
    ) -> None:
        """
        Store a WebSocket connection.

        Args:
            conn_id: API Gateway connection ID
            user_id: User identifier
            room_id: Room identifier (empty string if not yet in a room)
            connected_at_ms: Connection timestamp in epoch milliseconds
            user_name: Display name (optional, set from Cognito claims)
        """
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Calculate TTL (epoch seconds)
            ttl = (connected_at_ms // 1000) + self._ttl_seconds

            await table.put_item(
                Item={
                    "PK": schema.conn_pk(conn_id),
                    "SK": schema.conn_meta_sk(),
                    "conn_id": conn_id,
                    "user_id": user_id,
                    "user_name": user_name,
                    "room_id": room_id,
                    "connected_at_ms": connected_at_ms,
                    "ttl": ttl,
                    "GSI1_PK": schema.gsi1_room_pk(room_id),
                    "GSI1_SK": connected_at_ms,
                }
            )

    async def get(self, conn_id: str) -> dict[str, Any] | None:
        """
        Get a connection by ID.

        Args:
            conn_id: Connection identifier

        Returns:
            Connection dict with user_id, room_id, connected_at_ms, or None if not found
        """
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            response = await table.get_item(
                Key={
                    "PK": schema.conn_pk(conn_id),
                    "SK": schema.conn_meta_sk(),
                }
            )

            item = response.get("Item")
            if not item:
                return None

            return {
                "conn_id": item["conn_id"],
                "user_id": item["user_id"],
                "user_name": item.get("user_name", ""),
                "room_id": item["room_id"],
                "connected_at_ms": int(item["connected_at_ms"]),
            }

    async def delete(self, conn_id: str) -> None:
        """
        Delete a connection.

        Args:
            conn_id: Connection identifier
        """
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            await table.delete_item(
                Key={
                    "PK": schema.conn_pk(conn_id),
                    "SK": schema.conn_meta_sk(),
                }
            )

    async def list_by_room(self, room_id: str) -> list[dict[str, Any]]:
        """
        List all connections in a room using GSI1.

        Args:
            room_id: Room identifier

        Returns:
            List of connection dicts (may be empty)
        """
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            response = await table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1_PK = :gsi1_pk",
                ExpressionAttributeValues={":gsi1_pk": schema.gsi1_room_pk(room_id)},
                ScanIndexForward=True,  # Sort by connected_at_ms ascending
            )

            connections = []
            for item in response.get("Items", []):
                connections.append(
                    {
                        "conn_id": item["conn_id"],
                        "user_id": item["user_id"],
                        "room_id": item["room_id"],
                        "connected_at_ms": int(item["connected_at_ms"]),
                    }
                )

            return connections

    async def update_room(self, conn_id: str, new_room_id: str) -> None:
        """
        Update the room_id for a connection.

        This is used when a player moves between rooms (e.g., room merging).

        Args:
            conn_id: Connection identifier
            new_room_id: New room identifier
        """
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Get current connected_at_ms for GSI1_SK
            current = await self.get(conn_id)
            if not current:
                raise ValueError(f"Connection {conn_id} not found")

            await table.update_item(
                Key={
                    "PK": schema.conn_pk(conn_id),
                    "SK": schema.conn_meta_sk(),
                },
                UpdateExpression="SET room_id = :room_id, GSI1_PK = :gsi1_pk",
                ExpressionAttributeValues={
                    ":room_id": new_room_id,
                    ":gsi1_pk": schema.gsi1_room_pk(new_room_id),
                },
                ConditionExpression="attribute_exists(PK)",  # Ensure connection exists
            )
