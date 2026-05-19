"""DynamoDB implementation of WindowRepository port."""

import logging
from typing import Any

import aioboto3

from src.domain.entities import Prediction, PredictionWindow
from src.infrastructure.dynamodb import schema
from src.infrastructure.dynamodb.client import get_ddb_resource_kwargs

logger = logging.getLogger(__name__)


class WindowRepositoryDDB:
    """
    DynamoDB adapter for WindowRepository port.

    Item structure:
    - Window metadata: PK=WINDOW#<id>, SK=METADATA, room_id, game, prompt, opened_at_ms, deadline_ms, options, status
    - Prediction: PK=WINDOW#<id>, SK=SUBMISSION#<user_id>, value, submitted_at_ms
    - GSI1 for room queries: GSI1_PK=ROOM#<room_id>, GSI1_SK=<opened_at_ms>

    Uses single-table design with GSI1 for listing windows by room.
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

    async def get(self, window_id: str) -> PredictionWindow | None:
        """Get prediction window by ID."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            response = await table.get_item(
                Key={
                    "PK": schema.window_pk(window_id),
                    "SK": schema.window_meta_sk(),
                }
            )

            item = response.get("Item")
            if not item:
                return None

            return self._item_to_window(item)

    async def save(self, window: PredictionWindow) -> None:
        """Save or update a prediction window."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Build item
            item: dict[str, Any] = {
                "PK": schema.window_pk(window.window_id),
                "SK": schema.window_meta_sk(),
                "window_id": window.window_id,
                "room_id": window.room_id,
                "game": window.game,
                "prompt": window.prompt,
                "opened_at_ms": window.opened_at_ms,
                "deadline_ms": window.deadline_ms,
                "status": window.status,
                "GSI1_PK": schema.gsi1_room_pk(window.room_id),
                "GSI1_SK": window.opened_at_ms,
            }

            # Options can be None or tuple
            if window.options is not None:
                item["options"] = list(window.options)  # DynamoDB doesn't support tuples

            await table.put_item(Item=item)

    async def list_open_by_room(self, room_id: str) -> list[PredictionWindow]:
        """List all open prediction windows for a room using GSI1."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Query GSI1 for room's windows
            response = await table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1_PK = :gsi1_pk",
                ExpressionAttributeValues={":gsi1_pk": schema.gsi1_room_pk(room_id)},
                ScanIndexForward=True,  # Sort by opened_at_ms ascending
            )

            # Filter for open windows and convert to entities
            windows = []
            for item in response.get("Items", []):
                if item.get("SK") == schema.window_meta_sk() and item.get("status") == "open":
                    windows.append(self._item_to_window(item))

            return windows

    async def add_prediction(self, window_id: str, prediction: Prediction) -> None:
        """Add a prediction to a window."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            await table.put_item(
                Item={
                    "PK": schema.window_pk(window_id),
                    "SK": schema.submission_sk(prediction.user_id),
                    "window_id": window_id,
                    "user_id": prediction.user_id,
                    "value": prediction.value,
                    "submitted_at_ms": prediction.submitted_at_ms,
                }
            )

    async def list_predictions(self, window_id: str) -> list[Prediction]:
        """List all predictions for a window."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            # Query all items in window partition with SK starting with SUBMISSION#
            response = await table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk": schema.window_pk(window_id),
                    ":sk_prefix": "SUBMISSION#",
                },
            )

            predictions = []
            for item in response.get("Items", []):
                predictions.append(self._item_to_prediction(item))

            return predictions

    async def close(self, window_id: str, now_ms: int) -> None:
        """Close a prediction window by updating its status."""
        async with self._session.resource("dynamodb", **self._resource_kwargs) as ddb:
            table = await ddb.Table(self._table_name)

            await table.update_item(
                Key={
                    "PK": schema.window_pk(window_id),
                    "SK": schema.window_meta_sk(),
                },
                UpdateExpression="SET #status = :status",
                ExpressionAttributeNames={"#status": "status"},  # 'status' is a reserved word
                ExpressionAttributeValues={":status": "closed"},
                ConditionExpression="attribute_exists(PK)",  # Ensure window exists
            )

    def _item_to_window(self, item: dict[str, Any]) -> PredictionWindow:
        """Convert DynamoDB item to PredictionWindow entity."""
        # Convert options list back to tuple (or None)
        options = None
        if "options" in item and item["options"] is not None:
            options = tuple(item["options"])

        return PredictionWindow(
            window_id=item["window_id"],
            room_id=item["room_id"],
            game=item["game"],
            prompt=item["prompt"],
            opened_at_ms=int(item["opened_at_ms"]),
            deadline_ms=int(item["deadline_ms"]),
            options=options,
            status=item["status"],
        )

    def _item_to_prediction(self, item: dict[str, Any]) -> Prediction:
        """Convert DynamoDB item to Prediction entity."""
        return Prediction(
            window_id=item["window_id"],
            user_id=item["user_id"],
            value=item["value"],  # Can be str or int
            submitted_at_ms=int(item["submitted_at_ms"]),
        )
