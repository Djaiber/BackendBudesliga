"""API Gateway WebSocket broadcaster implementation."""

import asyncio
import json
import logging
from typing import Any

import aioboto3
from botocore.exceptions import ClientError

from ..dynamodb.connection_repository_ddb import ConnectionRepositoryDDB

logger = logging.getLogger(__name__)


class ApiGatewayBroadcaster:
    """
    API Gateway WebSocket adapter for WebSocketBroadcaster port.

    Sends messages to WebSocket connections using API Gateway Management API.
    Handles 410 GoneException for stale connections and broadcasts in parallel.
    """

    def __init__(
        self,
        api_endpoint: str,
        connection_repo: ConnectionRepositoryDDB,
        region: str = "eu-central-1",
    ) -> None:
        """
        Initialize broadcaster.

        Args:
            api_endpoint: API Gateway WebSocket endpoint (e.g., https://xxx.execute-api.region.amazonaws.com/prod)
            connection_repo: Connection repository for querying connections by room
            region: AWS region
        """
        self._api_endpoint = api_endpoint
        self._connection_repo = connection_repo
        self._region = region
        self._session = aioboto3.Session()

    async def send_to_connection(
        self,
        connection_id: str,
        message: dict[str, Any],
    ) -> None:
        """
        Send a message to a specific WebSocket connection.

        Args:
            connection_id: WebSocket connection identifier
            message: Message payload to send

        Raises:
            RuntimeError: If send fails (except for 410 GoneException)
        """
        try:
            async with self._session.client(
                "apigatewaymanagementapi",
                endpoint_url=self._api_endpoint,
                region_name=self._region,
            ) as client:
                await client.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message).encode("utf-8"),
                )
                logger.info(f"Sent message to connection: {connection_id}")

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            
            if error_code == "GoneException":
                # Connection is stale, delete it
                logger.warning(f"Connection {connection_id} is gone, deleting")
                await self._connection_repo.delete(connection_id)
            else:
                error_msg = f"Failed to send to connection {connection_id}: {e}"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from e

        except Exception as e:
            error_msg = f"Failed to send to connection {connection_id}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def broadcast_to_room(
        self,
        room_id: str,
        message: dict[str, Any],
    ) -> None:
        """
        Broadcast a message to all connections in a room.

        Sends messages in parallel and handles stale connections gracefully.

        Args:
            room_id: Room identifier
            message: Message payload to broadcast
        """
        # Get all connections in the room
        connections = await self._connection_repo.list_by_room(room_id)
        
        if not connections:
            logger.info(f"No connections found for room: {room_id}")
            return

        logger.info(f"Broadcasting to {len(connections)} connections in room: {room_id}")

        # Send to all connections in parallel
        tasks = [
            self._send_with_error_handling(conn["conn_id"], message)
            for conn in connections
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_with_error_handling(
        self,
        connection_id: str,
        message: dict[str, Any],
    ) -> None:
        """
        Send message with error handling (used for parallel broadcasts).

        Args:
            connection_id: WebSocket connection identifier
            message: Message payload to send
        """
        try:
            await self.send_to_connection(connection_id, message)
        except Exception as e:
            # Log but don't raise - we want other sends to continue
            logger.warning(f"Failed to send to {connection_id}: {e}")
