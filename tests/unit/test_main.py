"""Tests for the composition root (src/main.py)."""

from unittest.mock import patch


def test_build_container_returns_expected_top_level_keys():
    from src.main import build_container

    with patch("src.main.InfraConfig.from_env", return_value=_make_config()), \
            patch("src.main.RoomRepositoryDDB"), \
            patch("src.main.ScoreRepositoryDDB"), \
            patch("src.main.WindowRepositoryDDB"), \
            patch("src.main.ConnectionRepositoryDDB"), \
            patch("src.main.EventBridgePublisher"), \
            patch("src.main.NullBroadcaster"), \
            patch("src.main.PromptCache"), \
            patch("src.main.BedrockGenerator"):
        c = build_container()

    assert set(c.keys()) == {"config", "clock", "connections", "cognito", "broadcaster", "use_cases"}


def test_build_container_returns_all_use_cases():
    from src.main import build_container

    with patch("src.main.InfraConfig.from_env", return_value=_make_config()), \
            patch("src.main.RoomRepositoryDDB"), \
            patch("src.main.ScoreRepositoryDDB"), \
            patch("src.main.WindowRepositoryDDB"), \
            patch("src.main.ConnectionRepositoryDDB"), \
            patch("src.main.EventBridgePublisher"), \
            patch("src.main.NullBroadcaster"), \
            patch("src.main.PromptCache"), \
            patch("src.main.BedrockGenerator"):
        c = build_container()

    expected_use_cases = {
        "join_room", "leave_room", "submit_prediction", "open_window",
        "close_window", "close_expired_windows", "handle_match_event",
        "broadcast_emoji", "merge_rooms", "list_active_rooms",
    }
    assert set(c["use_cases"].keys()) == expected_use_cases


def test_build_container_uses_accept_any_token_validator_when_flag_set():
    from src.infrastructure.cognito.cognito_validator import AcceptAnyTokenValidator
    from src.main import build_container

    config = _make_config(accept_any_token=True)
    with patch("src.main.InfraConfig.from_env", return_value=config), \
            patch("src.main.RoomRepositoryDDB"), \
            patch("src.main.ScoreRepositoryDDB"), \
            patch("src.main.WindowRepositoryDDB"), \
            patch("src.main.ConnectionRepositoryDDB"), \
            patch("src.main.EventBridgePublisher"), \
            patch("src.main.NullBroadcaster"), \
            patch("src.main.PromptCache"), \
            patch("src.main.BedrockGenerator"):
        c = build_container()

    assert isinstance(c["cognito"], AcceptAnyTokenValidator)


def test_build_container_uses_cognito_validator_when_flag_false():
    from src.infrastructure.cognito.cognito_validator import CognitoValidator
    from src.main import build_container

    config = _make_config(accept_any_token=False)
    with patch("src.main.InfraConfig.from_env", return_value=config), \
            patch("src.main.RoomRepositoryDDB"), \
            patch("src.main.ScoreRepositoryDDB"), \
            patch("src.main.WindowRepositoryDDB"), \
            patch("src.main.ConnectionRepositoryDDB"), \
            patch("src.main.EventBridgePublisher"), \
            patch("src.main.NullBroadcaster"), \
            patch("src.main.PromptCache"), \
            patch("src.main.BedrockGenerator"):
        c = build_container()

    assert isinstance(c["cognito"], CognitoValidator)


def test_build_container_uses_null_broadcaster_when_no_ws_endpoint():
    from src.infrastructure.websocket.null_broadcaster import NullBroadcaster
    from src.main import build_container

    config = _make_config(websocket_api_endpoint=None)
    with patch("src.main.InfraConfig.from_env", return_value=config), \
            patch("src.main.RoomRepositoryDDB"), \
            patch("src.main.ScoreRepositoryDDB"), \
            patch("src.main.WindowRepositoryDDB"), \
            patch("src.main.ConnectionRepositoryDDB"), \
            patch("src.main.EventBridgePublisher"), \
            patch("src.main.PromptCache"), \
            patch("src.main.BedrockGenerator"):
        c = build_container()

    assert isinstance(c["broadcaster"], NullBroadcaster)


def test_build_container_uses_api_gateway_broadcaster_when_ws_endpoint_set():
    from src.infrastructure.websocket.api_gateway_broadcaster import ApiGatewayBroadcaster
    from src.main import build_container

    config = _make_config(websocket_api_endpoint="https://abc.execute-api.eu-central-1.amazonaws.com/prod")
    with patch("src.main.InfraConfig.from_env", return_value=config), \
            patch("src.main.RoomRepositoryDDB"), \
            patch("src.main.ScoreRepositoryDDB"), \
            patch("src.main.WindowRepositoryDDB"), \
            patch("src.main.ConnectionRepositoryDDB"), \
            patch("src.main.EventBridgePublisher"), \
            patch("src.main.PromptCache"), \
            patch("src.main.BedrockGenerator"):
        c = build_container()

    assert isinstance(c["broadcaster"], ApiGatewayBroadcaster)


def test_module_level_container_is_dict():
    import src.main as m

    assert isinstance(m.container, dict)
    assert "use_cases" in m.container


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides):  # type: ignore[no-untyped-def]
    from src.infrastructure.config import InfraConfig

    defaults = {
        "aws_region": "eu-central-1",
        "aws_account_id": "123456789012",
        "dynamodb_table": "test-table",
        "dynamodb_endpoint": None,
        "websocket_api_endpoint": None,
        "event_bus_name": "test-bus",
        "s3_replay_bucket": "test-bucket",
        "s3_endpoint": None,
        "bedrock_model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
        "bedrock_region": "us-east-1",
        "prompt_cache_ttl_seconds": 60,
        "cognito_user_pool_id": "eu-central-1_Test",
        "cognito_app_client_id": "testclient",
        "cognito_region": "eu-central-1",
        "replay_speed": 60,
        "replay_data_path": "/tmp/test",
        "prediction_window_duration_seconds": 20,
        "game_engine_tick_interval_seconds": 30,
        "min_players_per_room": 3,
        "max_players_per_room": 4,
        "max_leaderboard_merge_size": 25,
        "inactive_room_threshold_seconds": 300,
        "exact_prediction_points": 100,
        "closest_prediction_points": (50, 25, 10),
        "no_response_penalty": -10,
        "speed_multiplier_max": 1.1,
        "streak_3_multiplier": 1.2,
        "streak_5_multiplier": 1.5,
        "tier_enthusiast_min": 401,
        "tier_amateur_min": 701,
        "tier_savvy_min": 901,
        "log_level": "INFO",
        "log_format": "json",
        "local_mode": False,
        "accept_any_token": True,
    }
    defaults.update(overrides)
    return InfraConfig(**defaults)
