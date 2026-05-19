"""S3-based replay data loader with caching."""

import json
import logging
from typing import Any

import aioboto3

from ...domain.entities import MatchEvent

logger = logging.getLogger(__name__)


class ReplayLoader:
    """
    S3 adapter for loading match replay data.

    Loads match events from S3 JSON files with optional caching
    for Lambda cold-start reuse.
    """

    def __init__(
        self,
        bucket: str,
        region: str,
        endpoint_url: str | None = None,
        enable_cache: bool = True,
    ) -> None:
        """
        Initialize replay loader.

        Args:
            bucket: S3 bucket name containing replay data
            region: AWS region
            endpoint_url: Optional endpoint override for localstack
            enable_cache: Whether to cache loaded events in memory
        """
        self._bucket = bucket
        self._region = region
        self._endpoint_url = endpoint_url
        self._enable_cache = enable_cache
        self._session = aioboto3.Session()
        
        # In-memory cache for Lambda reuse
        self._cache: dict[str, list[MatchEvent]] = {}

    async def load_events(self, key: str) -> list[MatchEvent]:
        """
        Load match events from S3.

        Args:
            key: S3 object key (e.g., "events.json")

        Returns:
            List of MatchEvent entities sorted by (minute, second)

        Raises:
            ValueError: If JSON format is invalid or events cannot be parsed
            RuntimeError: If S3 operation fails
        """
        # Check cache first
        if self._enable_cache and key in self._cache:
            logger.info(f"Cache hit for key: {key}")
            return self._cache[key]

        logger.info(f"Loading events from S3: bucket={self._bucket}, key={key}")

        # Build client kwargs
        client_kwargs: dict[str, Any] = {"region_name": self._region}
        if self._endpoint_url:
            client_kwargs["endpoint_url"] = self._endpoint_url

        try:
            async with self._session.client("s3", **client_kwargs) as s3:
                # Get object from S3
                response = await s3.get_object(Bucket=self._bucket, Key=key)
                
                # Read body
                async with response["Body"] as stream:
                    body = await stream.read()
                
                # Parse JSON
                data = json.loads(body.decode("utf-8"))
                
                if not isinstance(data, list):
                    raise ValueError(f"Expected JSON array, got {type(data).__name__}")
                
                # Convert to MatchEvent entities
                events = []
                for idx, item in enumerate(data):
                    try:
                        event = MatchEvent(
                            event_id=item["event_id"],
                            minute=item["minute"],
                            second=item["second"],
                            event_type=item["event_type"],
                            team=item.get("team"),
                            player=item.get("player"),
                            x_position=item.get("x_position"),
                            y_position=item.get("y_position"),
                            metadata=item.get("metadata", {}),
                        )
                        events.append(event)
                    except (KeyError, ValueError, TypeError) as e:
                        logger.warning(f"Skipping invalid event at index {idx}: {e}")
                        continue
                
                logger.info(f"Loaded {len(events)} events from {key}")
                
                # Cache for future calls
                if self._enable_cache:
                    self._cache[key] = events
                
                return events
                
        except Exception as e:
            error_msg = f"Failed to load events from S3: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    async def load_match_info(self, key: str) -> dict[str, Any]:
        """
        Load match information from S3.

        Args:
            key: S3 object key (e.g., "match_info.json")

        Returns:
            Dictionary containing match metadata (teams, lineups, etc.)

        Raises:
            RuntimeError: If S3 operation fails
        """
        logger.info(f"Loading match info from S3: bucket={self._bucket}, key={key}")

        # Build client kwargs
        client_kwargs: dict[str, Any] = {"region_name": self._region}
        if self._endpoint_url:
            client_kwargs["endpoint_url"] = self._endpoint_url

        try:
            async with self._session.client("s3", **client_kwargs) as s3:
                # Get object from S3
                response = await s3.get_object(Bucket=self._bucket, Key=key)
                
                # Read body
                async with response["Body"] as stream:
                    body = await stream.read()
                
                # Parse JSON
                data = json.loads(body.decode("utf-8"))
                
                logger.info(f"Loaded match info from {key}")
                return data
                
        except Exception as e:
            error_msg = f"Failed to load match info from S3: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
        logger.info("Cache cleared")

    def get_cache_size(self) -> int:
        """Get the number of cached keys."""
        return len(self._cache)
