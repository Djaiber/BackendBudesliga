"""Infrastructure configuration from environment variables."""

import os
from dataclasses import dataclass


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""

    pass


@dataclass(frozen=True)
class InfraConfig:
    """
    Infrastructure configuration loaded from environment variables.

    All AWS-related configuration is centralized here. No other module
    should read os.environ directly.
    """

    # AWS
    aws_region: str
    aws_account_id: str

    # DynamoDB
    dynamodb_table: str
    dynamodb_endpoint: str | None

    # WebSocket API Gateway
    websocket_api_endpoint: str | None

    # EventBridge
    event_bus_name: str

    # S3
    s3_replay_bucket: str
    s3_endpoint: str | None

    # Bedrock AI
    bedrock_model_id: str
    bedrock_region: str
    prompt_cache_ttl_seconds: int

    # Cognito
    cognito_user_pool_id: str
    cognito_app_client_id: str
    cognito_region: str

    # Replay Engine
    replay_speed: int
    replay_data_path: str

    # Game Engine
    prediction_window_duration_seconds: int
    game_engine_tick_interval_seconds: int

    # Room Management
    min_players_per_room: int
    max_players_per_room: int
    max_leaderboard_merge_size: int
    inactive_room_threshold_seconds: int

    # Scoring
    exact_prediction_points: int
    closest_prediction_points: tuple[int, ...]
    no_response_penalty: int
    speed_multiplier_max: float

    # Streaks
    streak_3_multiplier: float
    streak_5_multiplier: float

    # Tiers
    tier_enthusiast_min: int
    tier_amateur_min: int
    tier_savvy_min: int

    # Logging
    log_level: str
    log_format: str

    # Local Development
    local_mode: bool
    accept_any_token: bool

    @classmethod
    def from_env(cls) -> "InfraConfig":
        """
        Load configuration from environment variables.

        Returns:
            InfraConfig instance

        Raises:
            ConfigError: If required variables are missing or invalid
        """

        def get_required(key: str) -> str:
            """Get required environment variable."""
            value = os.environ.get(key)
            if value is None or value == "":
                raise ConfigError(f"Required environment variable {key} is not set")
            return value

        def get_optional(key: str, default: str = "") -> str:
            """Get optional environment variable."""
            return os.environ.get(key, default)

        def get_int(key: str, default: int | None = None) -> int:
            """Get integer environment variable."""
            value = os.environ.get(key)
            if value is None or value == "":
                if default is not None:
                    return default
                raise ConfigError(f"Required environment variable {key} is not set")
            try:
                return int(value)
            except ValueError as err:
                raise ConfigError(
                    f"Environment variable {key} must be an integer, got: {value}"
                ) from err

        def get_float(key: str, default: float | None = None) -> float:
            """Get float environment variable."""
            value = os.environ.get(key)
            if value is None or value == "":
                if default is not None:
                    return default
                raise ConfigError(f"Required environment variable {key} is not set")
            try:
                return float(value)
            except ValueError as err:
                raise ConfigError(
                    f"Environment variable {key} must be a float, got: {value}"
                ) from err

        def get_bool(key: str, default: bool = False) -> bool:
            """Get boolean environment variable."""
            value = os.environ.get(key, "").lower()
            if value in ("true", "1", "yes"):
                return True
            elif value in ("false", "0", "no", ""):
                return False if value == "" else False
            return default

        def parse_int_list(value: str) -> tuple[int, ...]:
            """Parse comma-separated integers."""
            try:
                return tuple(int(x.strip()) for x in value.split(","))
            except ValueError as err:
                raise ConfigError(
                    f"CLOSEST_PREDICTION_POINTS must be comma-separated integers, got: {value}"
                ) from err

        # Parse closest prediction points
        closest_points_str = get_required("CLOSEST_PREDICTION_POINTS")
        closest_points = parse_int_list(closest_points_str)

        # Optional endpoints (empty string means None)
        dynamodb_endpoint = get_optional("DYNAMODB_ENDPOINT") or None
        s3_endpoint = get_optional("S3_ENDPOINT") or None
        websocket_api_endpoint = get_optional("WEBSOCKET_API_ENDPOINT") or None

        return cls(
            # AWS
            aws_region=get_required("AWS_REGION"),
            aws_account_id=get_required("AWS_ACCOUNT_ID"),
            # DynamoDB
            dynamodb_table=get_required("DYNAMODB_TABLE"),
            dynamodb_endpoint=dynamodb_endpoint,
            # WebSocket
            websocket_api_endpoint=websocket_api_endpoint,
            # EventBridge
            event_bus_name=get_required("EVENT_BUS_NAME"),
            # S3
            s3_replay_bucket=get_required("S3_REPLAY_BUCKET"),
            s3_endpoint=s3_endpoint,
            # Bedrock
            bedrock_model_id=get_required("BEDROCK_MODEL_ID"),
            bedrock_region=get_required("BEDROCK_REGION"),
            prompt_cache_ttl_seconds=get_int("PROMPT_CACHE_TTL_SECONDS", 60),
            # Cognito
            cognito_user_pool_id=get_required("COGNITO_USER_POOL_ID"),
            cognito_app_client_id=get_required("COGNITO_APP_CLIENT_ID"),
            cognito_region=get_required("COGNITO_REGION"),
            # Replay
            replay_speed=get_int("REPLAY_SPEED", 60),
            replay_data_path=get_required("REPLAY_DATA_PATH"),
            # Game Engine
            prediction_window_duration_seconds=get_int("PREDICTION_WINDOW_DURATION_SECONDS", 20),
            game_engine_tick_interval_seconds=get_int("GAME_ENGINE_TICK_INTERVAL_SECONDS", 30),
            # Room Management
            min_players_per_room=get_int("MIN_PLAYERS_PER_ROOM", 3),
            max_players_per_room=get_int("MAX_PLAYERS_PER_ROOM", 4),
            max_leaderboard_merge_size=get_int("MAX_LEADERBOARD_MERGE_SIZE", 25),
            inactive_room_threshold_seconds=get_int("INACTIVE_ROOM_THRESHOLD_SECONDS", 300),
            # Scoring
            exact_prediction_points=get_int("EXACT_PREDICTION_POINTS", 100),
            closest_prediction_points=closest_points,
            no_response_penalty=get_int("NO_RESPONSE_PENALTY", -10),
            speed_multiplier_max=get_float("SPEED_MULTIPLIER_MAX", 1.1),
            # Streaks
            streak_3_multiplier=get_float("STREAK_3_MULTIPLIER", 1.2),
            streak_5_multiplier=get_float("STREAK_5_MULTIPLIER", 1.5),
            # Tiers
            tier_enthusiast_min=get_int("TIER_ENTHUSIAST_MIN", 401),
            tier_amateur_min=get_int("TIER_AMATEUR_MIN", 701),
            tier_savvy_min=get_int("TIER_SAVVY_MIN", 901),
            # Logging
            log_level=get_optional("LOG_LEVEL", "INFO"),
            log_format=get_optional("LOG_FORMAT", "json"),
            # Local Development
            local_mode=get_bool("LOCAL_MODE", False),
            accept_any_token=get_bool("ACCEPT_ANY_TOKEN", False),
        )
