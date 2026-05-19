"""EventBridge implementation of EventPublisher port."""

import json
import logging
from typing import Any

import aioboto3

logger = logging.getLogger(__name__)


class EventBridgePublisher:
    """
    EventBridge adapter for EventPublisher port.

    Publishes domain events to AWS EventBridge using the PutEvents API.
    """

    def __init__(
        self,
        event_bus_name: str,
        region: str,
        endpoint_url: str | None = None,
    ) -> None:
        """
        Initialize publisher.

        Args:
            event_bus_name: EventBridge event bus name
            region: AWS region
            endpoint_url: Optional endpoint override for localstack
        """
        self._event_bus_name = event_bus_name
        self._region = region
        self._endpoint_url = endpoint_url
        self._session = aioboto3.Session()

    async def publish(
        self,
        source: str,
        detail_type: str,
        detail: dict[str, Any],
    ) -> None:
        """
        Publish a domain event to EventBridge.

        Args:
            source: Event source identifier (e.g., "connected-arena.game-engine")
            detail_type: Event type (e.g., "PredictionWindowOpened")
            detail: Event payload (will be JSON-serialized)
        """
        # Build client kwargs
        client_kwargs: dict[str, Any] = {"region_name": self._region}
        if self._endpoint_url:
            client_kwargs["endpoint_url"] = self._endpoint_url

        async with self._session.client("events", **client_kwargs) as events:
            # Build event entry
            entry = {
                "Source": source,
                "DetailType": detail_type,
                "Detail": json.dumps(detail),
                "EventBusName": self._event_bus_name,
            }

            # Publish event
            response = await events.put_events(Entries=[entry])

            # Check for failures
            if response.get("FailedEntryCount", 0) > 0:
                failed_entries = response.get("Entries", [])
                error_msg = f"Failed to publish event: {failed_entries}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            logger.info(
                f"Published event: source={source}, detail_type={detail_type}, "
                f"event_id={response['Entries'][0].get('EventId')}"
            )
