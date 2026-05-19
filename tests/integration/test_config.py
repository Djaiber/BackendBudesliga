"""Tests for infrastructure configuration."""

import os

import pytest

from src.infrastructure.config import ConfigError, InfraConfig


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear all environment variables."""
    for key in list(os.environ.keys()):
        if key.startswith(
            (
                "AWS_",
                "DYNAMODB_",
                "WEBSOCKET_",
                "EVENT_",
                "S3_",
                "BEDROCK_",
                "COGNITO_",
                "REPLAY_",
                "PREDICTION_",
                "GAME_",
                "MIN_",
                "MAX_",
                "INACTIVE_",
                "EXACT_",
                "CLOSEST_",
                "NO_",
                "SPEED_",
                "STREAK_",
                "TIER_",
                "LOG_",
                "LOCAL_",
            )
        ):
            monkeypatch.delenv(key, raising=False)


@pytest.fixture
def minimal_env(monkeypatch: pytest.MonkeyPatch, clean_env: None) -> None:
    """Set minimal required environment variables."""
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    monkeypatch.setenv("AWS_ACCOUNT_ID", "123456789012")
    monkeypatch.setenv("DYNAMODB_TABLE", "test-table")
    monkeypatch.setenv("EVENT_BUS_NAME", "test-bus")
    monkeypatch.setenv("S3_REPLAY_BUCKET", "test-bucket")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-2_test123")
    monkeypatch.setenv("COGNITO_APP_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("COGNITO_REGION", "us-east-2")
    monkeypatch.setenv("REPLAY_DATA_PATH", "/tmp/events.json")
    monkeypatch.setenv("CLOSEST_PREDICTION_POINTS", "50,30,20,10")


def test_from_env_with_minimal_config(minimal_env: None) -> None:
    """Test loading config with minimal required variables."""
    config = InfraConfig.from_env()

    assert config.aws_region == "us-east-2"
    assert config.aws_account_id == "123456789012"
    assert config.dynamodb_table == "test-table"
    assert config.event_bus_name == "test-bus"
    assert config.s3_replay_bucket == "test-bucket"
    assert config.bedrock_model_id == "anthropic.claude-3-haiku-20240307-v1:0"
    assert config.cognito_user_pool_id == "us-east-2_test123"

    # Check defaults
    assert config.prompt_cache_ttl_seconds == 60
    assert config.replay_speed == 60
    assert config.prediction_window_duration_seconds == 20
    assert config.local_mode is False
    assert config.log_level == "INFO"
    assert config.log_format == "json"


def test_from_env_missing_required_variable(
    monkeypatch: pytest.MonkeyPatch, clean_env: None
) -> None:
    """Test that missing required variable raises ConfigError."""
    # Set all but one required variable
    monkeypatch.setenv("AWS_REGION", "us-east-2")
    monkeypatch.setenv("AWS_ACCOUNT_ID", "123456789012")
    # Missing DYNAMODB_TABLE
    monkeypatch.setenv("EVENT_BUS_NAME", "test-bus")
    monkeypatch.setenv("S3_REPLAY_BUCKET", "test-bucket")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "test-model")
    monkeypatch.setenv("BEDROCK_REGION", "us-east-1")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "test-pool")
    monkeypatch.setenv("COGNITO_APP_CLIENT_ID", "test-client")
    monkeypatch.setenv("COGNITO_REGION", "us-east-2")
    monkeypatch.setenv("REPLAY_DATA_PATH", "/tmp/events.json")
    monkeypatch.setenv("CLOSEST_PREDICTION_POINTS", "50,30,20,10")

    with pytest.raises(ConfigError, match="DYNAMODB_TABLE"):
        InfraConfig.from_env()


def test_from_env_with_optional_endpoints(
    minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test loading config with optional endpoint overrides."""
    monkeypatch.setenv("DYNAMODB_ENDPOINT", "http://localhost:4566")
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:4566")
    monkeypatch.setenv("WEBSOCKET_API_ENDPOINT", "https://test.execute-api.us-east-2.amazonaws.com")

    config = InfraConfig.from_env()

    assert config.dynamodb_endpoint == "http://localhost:4566"
    assert config.s3_endpoint == "http://localhost:4566"
    assert config.websocket_api_endpoint == "https://test.execute-api.us-east-2.amazonaws.com"


def test_from_env_empty_optional_endpoints(
    minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that empty string endpoints are treated as None."""
    monkeypatch.setenv("DYNAMODB_ENDPOINT", "")
    monkeypatch.setenv("S3_ENDPOINT", "")
    monkeypatch.setenv("WEBSOCKET_API_ENDPOINT", "")

    config = InfraConfig.from_env()

    assert config.dynamodb_endpoint is None
    assert config.s3_endpoint is None
    assert config.websocket_api_endpoint is None


def test_from_env_with_custom_values(minimal_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test loading config with custom non-default values."""
    monkeypatch.setenv("PROMPT_CACHE_TTL_SECONDS", "120")
    monkeypatch.setenv("REPLAY_SPEED", "30")
    monkeypatch.setenv("PREDICTION_WINDOW_DURATION_SECONDS", "15")
    monkeypatch.setenv("MIN_PLAYERS_PER_ROOM", "2")
    monkeypatch.setenv("MAX_PLAYERS_PER_ROOM", "6")
    monkeypatch.setenv("EXACT_PREDICTION_POINTS", "200")
    monkeypatch.setenv("SPEED_MULTIPLIER_MAX", "1.5")
    monkeypatch.setenv("STREAK_3_MULTIPLIER", "1.3")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LOG_FORMAT", "text")
    monkeypatch.setenv("LOCAL_MODE", "true")

    config = InfraConfig.from_env()

    assert config.prompt_cache_ttl_seconds == 120
    assert config.replay_speed == 30
    assert config.prediction_window_duration_seconds == 15
    assert config.min_players_per_room == 2
    assert config.max_players_per_room == 6
    assert config.exact_prediction_points == 200
    assert config.speed_multiplier_max == 1.5
    assert config.streak_3_multiplier == 1.3
    assert config.log_level == "DEBUG"
    assert config.log_format == "text"
    assert config.local_mode is True


def test_from_env_invalid_integer(minimal_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that invalid integer raises ConfigError."""
    monkeypatch.setenv("REPLAY_SPEED", "not-a-number")

    with pytest.raises(ConfigError, match="REPLAY_SPEED.*integer"):
        InfraConfig.from_env()


def test_from_env_invalid_float(minimal_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that invalid float raises ConfigError."""
    monkeypatch.setenv("SPEED_MULTIPLIER_MAX", "not-a-float")

    with pytest.raises(ConfigError, match="SPEED_MULTIPLIER_MAX.*float"):
        InfraConfig.from_env()


def test_from_env_parse_closest_prediction_points(
    minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test parsing comma-separated closest prediction points."""
    monkeypatch.setenv("CLOSEST_PREDICTION_POINTS", "60,40,25,15,5")

    config = InfraConfig.from_env()

    assert config.closest_prediction_points == (60, 40, 25, 15, 5)


def test_from_env_invalid_closest_prediction_points(
    minimal_env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that invalid closest prediction points raises ConfigError."""
    monkeypatch.setenv("CLOSEST_PREDICTION_POINTS", "50,not-a-number,20")

    with pytest.raises(ConfigError, match="CLOSEST_PREDICTION_POINTS.*integers"):
        InfraConfig.from_env()


def test_from_env_boolean_variations(minimal_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test various boolean value formats."""
    # Test true values
    for true_val in ["true", "True", "TRUE", "1", "yes", "Yes"]:
        monkeypatch.setenv("LOCAL_MODE", true_val)
        config = InfraConfig.from_env()
        assert config.local_mode is True, f"Failed for value: {true_val}"

    # Test false values
    for false_val in ["false", "False", "FALSE", "0", "no", "No", ""]:
        monkeypatch.setenv("LOCAL_MODE", false_val)
        config = InfraConfig.from_env()
        assert config.local_mode is False, f"Failed for value: {false_val}"


def test_config_is_frozen(minimal_env: None) -> None:
    """Test that config is immutable."""
    config = InfraConfig.from_env()

    with pytest.raises(Exception):  # dataclass frozen raises FrozenInstanceError
        config.aws_region = "us-west-2"  # type: ignore
