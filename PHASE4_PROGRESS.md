# Phase 4 Progress: Infrastructure Adapters

## Status: IN PROGRESS (Deliverables 1-6 Complete)

Phase 4 implements AWS-backed adapters for all domain ports. This document tracks progress through the 17-step deliverable sequence.

**Latest Update**: Deliverables 4-6 complete - all three DynamoDB repositories implemented with 100% test coverage using unittest.mock approach.

## Completed ✅

### 1. Configuration (config.py + tests) ✅
- **File**: `src/infrastructure/config.py`
- **Tests**: `tests/integration/test_config.py` (11 tests, all passing)
- **Features**:
  - `InfraConfig.from_env()` - loads all config from environment variables
  - `ConfigError` - raised when required variables missing or invalid
  - Validates all required AWS configuration
  - Supports optional endpoint overrides for local development
  - Parses complex types (int lists, booleans, floats)
  - Frozen dataclass (immutable)
- **Environment Variables**: Reads 40+ variables matching `.env.example` exactly
- **Coverage**: 94% (3 lines unreachable in error paths)

### 2. DynamoDB Schema (schema.py + tests) ✅
- **File**: `src/infrastructure/dynamodb/schema.py`
- **Tests**: `tests/integration/dynamodb/test_schema.py` (17 tests, all passing)
- **Features**:
  - Pure functions for building PK/SK keys
  - Single-table design with clear entity patterns
  - GSI1 keys for status and room-based queries
  - Comprehensive docstrings explaining table structure
- **Key Patterns**:
  - Rooms: `PK=ROOM#<id>, SK=METADATA` or `SK=PLAYER#<user_id>`
  - Users: `PK=USER#<user_id>, SK=PROFILE`
  - Connections: `PK=CONN#<conn_id>, SK=METADATA`
  - Windows: `PK=WINDOW#<id>, SK=METADATA` or `SK=SUBMISSION#<user_id>`
  - Cache: `PK=CACHE#PROMPT, SK=<cache_key>`
- **GSI1 Patterns**:
  - Status queries: `GSI1_PK=STATUS#<status>, GSI1_SK=<created_at_ms>`
  - Room queries: `GSI1_PK=ROOM#<room_id>, GSI1_SK=<created_at_ms>`
- **Coverage**: 100%

### 3. DynamoDB Client Builder (client.py + tests) ✅
- **File**: `src/infrastructure/dynamodb/client.py`
- **Tests**: `tests/integration/dynamodb/test_client.py` (4 tests, all passing)
- **Features**:
  - `build_ddb_resource()` - creates aioboto3 session
  - `get_ddb_resource_kwargs()` - builds kwargs for resource creation
  - Support for endpoint override (localstack)
  - Clean separation of session creation and configuration
- **Coverage**: 100%

### Dependencies Added ✅
Updated `pyproject.toml`:
- **Production**: `aioboto3>=12.0.0`, `requests>=2.31.0`
- **Development**: `responses>=0.24.0`, `types-requests>=2.31.0`

### 3. DynamoDB Client Builder ✅
- **File**: `src/infrastructure/dynamodb/client.py`
- **Tests**: `tests/integration/dynamodb/test_client.py` (4 tests, all passing)
- **Features**:
  - `build_ddb_resource()` - creates aioboto3 session
  - `get_ddb_resource_kwargs()` - builds kwargs for resource creation
  - Support for endpoint override (localstack)
  - Clean separation of session creation and configuration
- **Coverage**: 100%

### 4. Room Repository DDB ✅
- **File**: `src/infrastructure/dynamodb/room_repository_ddb.py`
- **Tests**: `tests/integration/dynamodb/test_room_repository_ddb.py` (11 tests, all passing)
- **Implements**: `RoomRepository` port
- **Methods**: get, save, list_by_status, add_player, remove_player, delete
- **Features**:
  - Single-table design with room metadata + player items
  - GSI1 for status-based queries (sorted by created_at)
  - Batch operations for efficient multi-item writes
  - Re-reads room after add/remove player operations
- **Coverage**: 99% (1 line unreachable in error path)

### 5. Score Repository DDB ✅
- **File**: `src/infrastructure/dynamodb/score_repository_ddb.py`
- **Tests**: `tests/integration/dynamodb/test_score_repository_ddb.py` (9 tests, all passing)
- **Implements**: `ScoreRepository` port
- **Methods**: get_player, upsert_player, apply_delta (atomic), leaderboard
- **Features**:
  - User profile items with score, tier, streak
  - Atomic score updates using UpdateItem with ConditionExpression
  - GSI1 for room-based leaderboard queries (sorted by score)
  - Handles negative points (penalties)
- **Coverage**: 100%

### 6. Window Repository DDB ✅
- **File**: `src/infrastructure/dynamodb/window_repository_ddb.py`
- **Tests**: `tests/integration/dynamodb/test_window_repository_ddb.py` (12 tests, all passing)
- **Implements**: `WindowRepository` port
- **Methods**: get, save, list_open_by_room, add_prediction, list_predictions, close
- **Features**:
  - Window metadata + prediction submission items
  - GSI1 for room-based window queries (sorted by opened_at_ms)
  - Handles both string and integer prediction values
  - Converts tuple options to/from DynamoDB lists
  - Uses reserved word workaround for 'status' attribute
- **Coverage**: 100%

## Next Steps (Remaining 11 deliverables)

### 7. Connection Repository DDB (NEW - not a domain port)
- **File**: `src/infrastructure/dynamodb/connection_repository_ddb.py`
- **Tests**: `tests/integration/dynamodb/test_connection_repository_ddb.py`
- **Purpose**: Track WebSocket connections (AWS-specific, not in domain)
- **Methods**: put, get, delete, list_by_room, update_room
- **TTL**: 1 hour automatic expiration

### 8. Clock + ID Generator
- **Files**: `src/infrastructure/clock/system_clock.py`, `src/infrastructure/id_generator/uuid_id_generator.py`
- **Tests**: Small unit tests
- **Implements**: `Clock` and `IdGenerator` ports

### 9. EventBridge Publisher
- **File**: `src/infrastructure/eventbridge/eventbridge_publisher.py`
- **Tests**: `tests/integration/eventbridge/test_eventbridge_publisher.py`
- **Implements**: `EventPublisher` port
- **Uses**: boto3 EventBridge `put_events`

### 10. S3 Replay Loader
- **File**: `src/infrastructure/s3/replay_loader.py`
- **Tests**: `tests/integration/s3/test_replay_loader.py`
- **Purpose**: Load match events from S3 JSON files
- **Features**: Caching for Lambda cold-start reuse

### 11. WebSocket Broadcaster
- **File**: `src/infrastructure/websocket/api_gateway_broadcaster.py`
- **Tests**: `tests/integration/websocket/test_api_gateway_broadcaster.py`
- **Implements**: `WebSocketBroadcaster` port
- **Uses**: ApiGatewayManagementApi `post_to_connection`
- **Features**: Handle 410 GoneException, parallel broadcasts

### 12. Prompt Cache
- **File**: `src/infrastructure/ai/prompt_cache.py`
- **Tests**: `tests/integration/ai/test_prompt_cache.py`
- **Purpose**: DynamoDB-backed cache for AI prompts
- **TTL**: 60 seconds (configurable)

### 13. Bedrock Generator
- **File**: `src/infrastructure/ai/bedrock_generator.py`
- **Tests**: `tests/integration/ai/test_bedrock_generator.py`
- **Implements**: `AIGenerator` port
- **Uses**: AWS Bedrock with Claude 3 Haiku
- **Features**: Prompt caching, game-specific options

### 14. Replay Engine
- **Files**: `src/infrastructure/replay/xml_parser.py`, `src/infrastructure/replay/replay_engine.py`
- **Tests**: `tests/integration/replay/test_*.py`
- **Purpose**: Parse XML events and replay them in real-time
- **Features**: Configurable speed factor, async event publishing

### 15. Cognito Validator
- **File**: `src/infrastructure/auth/cognito_validator.py`
- **Tests**: `tests/integration/auth/test_cognito_validator.py`
- **Purpose**: Validate Cognito JWT tokens
- **Uses**: PyJWT + JWKS from Cognito
- **Features**: JWKS caching (1 hour), signature verification

### 16. Smoke Tests
- **Files**: `scripts/smoke_test_*.py` (one per major adapter)
- **Purpose**: Manual validation against real AWS sandbox
- **NOT run by pytest** - explicit manual execution
- **Examples**: smoke_test_dynamodb.py, smoke_test_eventbridge.py, smoke_test_bedrock.py

### 17. Full Test Suite
- **Goal**: All Phase 2 + Phase 3 + Phase 4 tests passing
- **Command**: `make test`
- **Expected**: 98 (Phase 2) + 43 (Phase 3) + ~50 (Phase 4) = ~191 tests

## Architecture Principles

### Zero Domain Logic in Adapters ✅
- Adapters only translate between domain types and AWS APIs
- No business rules, no calculations, no decisions
- Pure I/O translation layer

### Zero Direct os.environ Access ✅
- All configuration through `InfraConfig.from_env()`
- No adapter reads environment variables directly
- Centralized configuration management

### Zero Real AWS Calls in Tests ✅
- All integration tests use `moto` or `unittest.mock`
- Smoke tests are separate, manual, explicit
- Fast, deterministic, offline-capable tests

### Type Safety ✅
- All adapters have complete type hints
- `mypy --strict` must pass
- Structured logging (JSON format)

### Async All The Way ✅
- All adapter methods are async
- Use `aioboto3` for async boto3 operations
- No sync boto3 inside async def

## Test Results

```bash
# Config tests
pytest tests/integration/test_config.py -v
# ✅ 11 passed in 0.28s

# Schema tests
pytest tests/integration/dynamodb/test_schema.py -v
# ✅ 17 passed in 0.17s

# Client tests
pytest tests/integration/dynamodb/test_client.py -v
# ✅ 4 passed in 0.41s

# Room Repository tests
pytest tests/integration/dynamodb/test_room_repository_ddb.py -v
# ✅ 11 passed in 0.46s (99% coverage)

# Score Repository tests
pytest tests/integration/dynamodb/test_score_repository_ddb.py -v
# ✅ 9 passed in 0.49s (100% coverage)

# Window Repository tests
pytest tests/integration/dynamodb/test_window_repository_ddb.py -v
# ✅ 12 passed in 0.50s (100% coverage)

# All DynamoDB tests
pytest tests/integration/dynamodb/ -v
# ✅ 53 passed in 0.56s

# Total so far
# ✅ 64 integration tests passing (11 config + 53 dynamodb)
```

## File Structure (Current)

```
src/infrastructure/
├── __init__.py
├── config.py ✅
└── dynamodb/
    ├── __init__.py
    ├── schema.py ✅
    ├── client.py ✅
    ├── room_repository_ddb.py ✅
    ├── score_repository_ddb.py ✅
    └── window_repository_ddb.py ✅

tests/integration/
├── __init__.py
├── test_config.py ✅ (11 tests)
└── dynamodb/
    ├── __init__.py
    ├── test_schema.py ✅ (17 tests)
    ├── test_client.py ✅ (4 tests)
    ├── test_room_repository_ddb.py ✅ (11 tests)
    ├── test_score_repository_ddb.py ✅ (9 tests)
    └── test_window_repository_ddb.py ✅ (12 tests)
```

## Estimated Remaining Effort

- **DynamoDB Repositories** (4 repos): ~2-3 hours
- **Simple Adapters** (Clock, ID, EventBridge): ~30 minutes
- **Complex Adapters** (WebSocket, Bedrock, Replay): ~2 hours
- **Cognito Validator**: ~1 hour
- **Smoke Tests**: ~1 hour
- **Integration & Debugging**: ~1 hour
- **Total**: ~7-8 hours

## Success Criteria

When Phase 4 is complete:
- ✅ `make lint` - ruff clean on all infrastructure code
- ✅ `make typecheck` - mypy --strict passes
- ✅ `make test` - all unit + integration tests green (no AWS calls)
- ✅ Every domain port has a working AWS adapter
- ✅ Smoke tests documented and ready for sandbox validation
- ✅ Phase 2 + Phase 3 tests still passing

## Notes

- **Phase 3 Signature Issues**: Phase 3 tests have entity signature mismatches (documented in PHASE3_STATUS.md). These should be fixed before Phase 5, but don't block Phase 4 infrastructure work.
- **Testing Approach Changed**: Initially tried moto with aioboto3 but encountered async incompatibility. Switched to unittest.mock for all repository tests - works perfectly and is faster.
- **Moto Limitations**: ApiGatewayManagementApi not well-mocked by moto - use unittest.mock.patch for WebSocket broadcaster tests.
- **Bedrock Testing**: Patch boto3 client, assert request body shape, return fixed JSON responses.
- **Local Development**: All adapters support endpoint overrides via config for localstack testing.

## Next Commit

Will include:
- Connection Repository (deliverable 7) - WebSocket connection tracking
- Clock + ID generator adapters (deliverable 8) - simple implementations
- Progress toward remaining deliverables
