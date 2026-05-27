"""Composition root: wires every domain port to its infrastructure adapter.

This module is imported by every Lambda handler. It runs ONCE per cold start
and produces a `container` dict with fully-wired use cases ready to invoke.
"""

from __future__ import annotations

import logging
from typing import Any

from src.application.use_cases import (
    BroadcastEmojiUseCase,
    CloseExpiredWindowsUseCase,
    ClosePredictionWindowUseCase,
    HandleMatchEventUseCase,
    JoinRoomUseCase,
    LeaveRoomUseCase,
    ListActiveRoomsUseCase,
    MergeInactiveRoomsUseCase,
    OpenPredictionWindowUseCase,
    SubmitPredictionUseCase,
)
from src.infrastructure.ai.bedrock_generator import BedrockGenerator
from src.infrastructure.ai.prompt_cache import PromptCache
from src.infrastructure.clock.system_clock import SystemClock
from src.infrastructure.cognito.cognito_validator import AcceptAnyTokenValidator, CognitoValidator
from src.infrastructure.config import InfraConfig
from src.infrastructure.dynamodb.connection_repository_ddb import ConnectionRepositoryDDB
from src.infrastructure.dynamodb.room_repository_ddb import RoomRepositoryDDB
from src.infrastructure.dynamodb.score_repository_ddb import ScoreRepositoryDDB
from src.infrastructure.dynamodb.window_repository_ddb import WindowRepositoryDDB
from src.infrastructure.eventbridge.eventbridge_publisher import EventBridgePublisher
from src.infrastructure.id_generator.uuid_id_generator import UuidIdGenerator
from src.infrastructure.websocket.api_gateway_broadcaster import ApiGatewayBroadcaster
from src.infrastructure.websocket.null_broadcaster import NullBroadcaster

logger = logging.getLogger(__name__)


def build_container() -> dict[str, Any]:
    """Build and return the fully-wired dependency container.

    Called once at cold start. All Lambda warm invocations reuse the result.
    """
    config = InfraConfig.from_env()

    # Infrastructure primitives
    clock = SystemClock()
    id_gen = UuidIdGenerator()

    # DynamoDB repositories
    rooms = RoomRepositoryDDB(
        table_name=config.dynamodb_table,
        region=config.aws_region,
        endpoint_url=config.dynamodb_endpoint,
    )
    scores = ScoreRepositoryDDB(
        table_name=config.dynamodb_table,
        region=config.aws_region,
        endpoint_url=config.dynamodb_endpoint,
    )
    windows = WindowRepositoryDDB(
        table_name=config.dynamodb_table,
        region=config.aws_region,
        endpoint_url=config.dynamodb_endpoint,
    )
    connections = ConnectionRepositoryDDB(
        table_name=config.dynamodb_table,
        region=config.aws_region,
        endpoint_url=config.dynamodb_endpoint,
    )

    # EventBridge publisher
    publisher = EventBridgePublisher(
        event_bus_name=config.event_bus_name,
        region=config.aws_region,
    )

    # WebSocket broadcaster (NullBroadcaster when no endpoint is configured)
    from src.domain.ports import WebSocketBroadcaster  # local import avoids circular ref

    broadcaster: WebSocketBroadcaster
    if config.websocket_api_endpoint:
        broadcaster = ApiGatewayBroadcaster(
            api_endpoint=config.websocket_api_endpoint,
            connection_repo=connections,
            region=config.aws_region,
        )
    else:
        broadcaster = NullBroadcaster()

    # Bedrock AI generator with DynamoDB-backed prompt cache
    prompt_cache = PromptCache(
        table_name=config.dynamodb_table,
        ttl_seconds=config.prompt_cache_ttl_seconds,
        clock=clock,
        region=config.aws_region,
        endpoint_url=config.dynamodb_endpoint,
    )
    ai_generator = BedrockGenerator(
        model_id=config.bedrock_model_id,
        region=config.bedrock_region,
        prompt_cache=prompt_cache,
    )

    # Cognito validator (dev bypass via ACCEPT_ANY_TOKEN=true)
    from src.infrastructure.cognito.cognito_validator import (  # noqa: F811
        AcceptAnyTokenValidator,
        CognitoValidator,
    )

    if config.accept_any_token:
        cognito: AcceptAnyTokenValidator | CognitoValidator = AcceptAnyTokenValidator()
    else:
        cognito = CognitoValidator(
            user_pool_id=config.cognito_user_pool_id,
            app_client_id=config.cognito_app_client_id,
            region=config.cognito_region,
        )

    # Use cases
    join_room = JoinRoomUseCase(
        room_repo=rooms,
        score_repo=scores,
        broadcaster=broadcaster,
        id_gen=id_gen,
        clock=clock,
    )
    leave_room = LeaveRoomUseCase(room_repo=rooms, broadcaster=broadcaster)
    submit_prediction = SubmitPredictionUseCase(window_repo=windows, clock=clock)
    open_window = OpenPredictionWindowUseCase(
        window_repo=windows,
        broadcaster=broadcaster,
        ai_gen=ai_generator,
        id_gen=id_gen,
        clock=clock,
    )
    close_window = ClosePredictionWindowUseCase(
        window_repo=windows,
        room_repo=rooms,
        score_repo=scores,
        broadcaster=broadcaster,
        clock=clock,
    )
    close_expired = CloseExpiredWindowsUseCase(
        window_repo=windows,
        close_window=close_window,
        clock=clock,
    )
    handle_match_event = HandleMatchEventUseCase(
        room_repo=rooms,
        broadcaster=broadcaster,
        event_publisher=publisher,
    )
    broadcast_emoji = BroadcastEmojiUseCase(
        room_repo=rooms,
        score_repo=scores,
        broadcaster=broadcaster,
    )
    merge_rooms = MergeInactiveRoomsUseCase(
        room_repo=rooms,
        broadcaster=broadcaster,
        clock=clock,
    )
    list_active_rooms = ListActiveRoomsUseCase(room_repo=rooms)

    logger.info("Composition root built successfully")

    return {
        "config": config,
        "clock": clock,
        "connections": connections,
        "cognito": cognito,
        "broadcaster": broadcaster,
        "use_cases": {
            "join_room": join_room,
            "leave_room": leave_room,
            "submit_prediction": submit_prediction,
            "open_window": open_window,
            "close_window": close_window,
            "close_expired_windows": close_expired,
            "handle_match_event": handle_match_event,
            "broadcast_emoji": broadcast_emoji,
            "merge_rooms": merge_rooms,
            "list_active_rooms": list_active_rooms,
        },
    }


# Module-level singleton — runs once per cold start
container: dict[str, Any] = build_container()
