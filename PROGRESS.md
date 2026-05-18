# BackendBudes Development Progress

## Phase 1: Foundation & Data Ingestion ✅ COMPLETE

### Completed Items

#### 1. Project Setup
- ✅ README.md with comprehensive documentation
- ✅ pyproject.toml with all dependencies (boto3, pydantic, pyjwt, pytest, moto, ruff, mypy)
- ✅ Makefile with targets: install, test, lint, typecheck, format, convert-xml, run-local-replay
- ✅ .env.example with all configuration variables
- ✅ .python-version pinned to 3.11
- ✅ docker-compose.yml for localstack
- ✅ .gitignore updated with project-specific entries

#### 2. Data Conversion Script
- ✅ `scripts/convert_xml_to_json.py` - Converts XML match data to normalized JSON
  - Reads Events_Anonym.xml (1,635 events parsed)
  - Reads MatchInformations_Anonym.xml (teams, lineups, metadata)
  - Reads kpi_data_Bayern_Hamburg.xml (KPI snapshots)
  - Outputs to `scripts/output/`:
    - `events.json` - Sorted by (minute, second), normalized event types
    - `match_info.json` - Teams, lineups, match metadata
    - `kpi.json` - KPI snapshots indexed by minute
  - Handles XML files with comment lines at the beginning
  - Normalizes event types (PASS, SHOT, GOAL, CORNER_KICK, etc.)
  - Extracts metadata for each event

#### 3. S3 Upload Script
- ✅ `scripts/upload_to_s3.sh` - Uploads converted JSON to S3
  - Creates bucket if it doesn't exist
  - Uploads all three JSON files
  - Configurable via environment variables

### Testing Phase 1

```bash
# Convert XML to JSON
make convert-xml
# or
python scripts/convert_xml_to_json.py

# Expected output:
# - scripts/output/events.json (1,635 events, ~1.2MB)
# - scripts/output/match_info.json (~11KB)
# - scripts/output/kpi.json (minimal data)

# Upload to S3 (requires AWS credentials)
./scripts/upload_to_s3.sh
```

### Verified Output

Sample event from `events.json`:
```json
{
  "event_id": "18902400000007",
  "minute": 0,
  "second": 0,
  "event_type": "PASS",
  "team": "DFL-CLU-000002",
  "player": "DFL-OBJ-000025",
  "x_position": 52.9,
  "y_position": 33.5,
  "timestamp": "2025-01-01T16:30:19.566+02:00",
  "metadata": {
    "Play": {
      "Recipient": "DFL-OBJ-000010",
      "Team": "DFL-CLU-000002",
      "Height": "high",
      "Distance": "long",
      "Evaluation": "unsuccessful"
    }
  }
}
```

---

## Phase 2: Domain Layer (Pure Python) ✅ COMPLETE

### Completed Items

#### Domain Entities (`src/domain/entities/`)
- ✅ `match_event.py` - Match event entity with validation
- ✅ `player.py` - Player entity (userId, name, score, tier, streak)
- ✅ `room.py` - Room entity (3-4 players) with `is_mergeable()` helper
- ✅ `prediction_window.py` - Prediction window entity with `is_expired()` helper
- ✅ `prediction.py` - Player prediction entity
- ✅ `score.py` - Score delta entity

#### Domain Services (`src/domain/services/`)
- ✅ `tier_service.py` - Tier calculation (Dummies/Enthusiast/Amateur/Savvy)
- ✅ `streak_service.py` - Streak tracking (3→1.2x, 5→1.5x multipliers)
- ✅ `scoring_service.py` - Score calculation with speed multipliers
- ✅ `matchmaker_service.py` - Room matching and merging logic
- ✅ `game_engine_service.py` - Mini-game selection and resolution

#### Domain Ports (`src/domain/ports/`)
- ✅ `room_repository.py` - Abstract room storage interface (Protocol)
- ✅ `score_repository.py` - Abstract score storage interface (Protocol)
- ✅ `event_publisher.py` - Abstract event publishing interface (Protocol)
- ✅ `ai_generator.py` - Abstract AI prompt generation interface (Protocol)
- ✅ `websocket_broadcaster.py` - Abstract WebSocket broadcast interface (Protocol)

#### Unit Tests (`tests/unit/`)
- ✅ All entity tests (33 tests) - 100% coverage on entities
- ✅ All service tests (65 tests) - 97-100% coverage on services
- ✅ **Total: 98 tests passing**

### Test Results

```bash
# All tests passing
pytest tests/unit/ -v
# 98 passed in 0.16s

# Coverage
# Entities: 100%
# Services: 97-100% (unreachable branches protected by entity validation)

# Type checking
mypy src/domain/ --strict --explicit-package-bases
# Success: no issues found in 20 source files

# Linting
ruff check src/domain/ tests/unit/
# All checks passed!
```

### Architecture Compliance ✅

- **Zero AWS imports**: Domain layer is pure Python
- **Zero I/O**: All services are synchronous and deterministic
- **Type safety**: mypy --strict passes on all domain code
- **Immutability**: All entities are frozen dataclasses
- **Testability**: 100% unit testable with no mocks needed
- **Ports as Protocols**: Structural typing for dependency inversion

---

## Phase 2: Domain Layer (Pure Python) 🔄 NEXT

### To Build

#### Domain Entities (`src/domain/entities/`)
- [ ] `match_event.py` - Match event entity
- [ ] `room.py` - Room entity (3-4 players)
- [ ] `player.py` - Player entity (userId, name, score, tier, streak)
- [ ] `prediction_window.py` - Prediction window entity
- [ ] `prediction.py` - Player prediction entity
- [ ] `score.py` - Score calculation entity

#### Domain Services (`src/domain/services/`)
- [ ] `scoring_service.py` - Score calculation logic
  - Exact prediction: 100 points
  - Closest non-exact: 50, 30, 20, 10
  - No response: -10 penalty
  - Speed multiplier: up to x1.1
- [ ] `streak_service.py` - Streak tracking
  - 3 correct → x1.2 multiplier
  - 5 correct → x1.5 multiplier
  - Wrong answer resets streak
- [ ] `tier_service.py` - Tier management
  - Dummies: 0-400
  - Enthusiast: 401-700
  - Amateur: 701-900
  - Savvy: 901-1200
- [ ] `matchmaker_service.py` - Room matching logic
  - 3-4 players per room
  - Merge rooms with <3 players
  - Max 25 fans in leaderboard merge
- [ ] `game_engine_service.py` - Mini-game selection logic

#### Domain Ports (`src/domain/ports/`)
- [ ] `room_repository.py` - Abstract room storage interface
- [ ] `score_repository.py` - Abstract score storage interface
- [ ] `event_publisher.py` - Abstract event publishing interface
- [ ] `ai_generator.py` - Abstract AI prompt generation interface
- [ ] `websocket_broadcaster.py` - Abstract WebSocket broadcast interface

#### Unit Tests
- [ ] `tests/unit/entities/` - Test all entities
- [ ] `tests/unit/services/` - Test all services (100% coverage target)

---

## Phase 3: Application Layer 🔜 UPCOMING

### To Build

#### Use Cases (`src/application/use_cases/`)
- [ ] `join_room.py` - Handle player joining
- [ ] `submit_prediction.py` - Handle prediction submission
- [ ] `open_prediction_window.py` - Open new prediction window
- [ ] `close_prediction_window.py` - Close window and calculate results
- [ ] `handle_match_event.py` - Process match events from replay
- [ ] `broadcast_emoji.py` - Broadcast emoji to room
- [ ] `merge_inactive_rooms.py` - Merge rooms with <3 players

#### DTOs (`src/application/dto/`)
- [ ] `messages.py` - Request/response message shapes

#### Tests
- [ ] `tests/unit/use_cases/` - Test with fake port implementations

---

## Phase 4: Infrastructure Adapters 🔜 UPCOMING

### To Build

#### AWS Adapters (`src/infrastructure/`)
- [ ] `websocket/api_gateway_broadcaster.py` - WebSocket broadcaster
- [ ] `dynamodb/room_repository_ddb.py` - DynamoDB room repository
- [ ] `dynamodb/score_repository_ddb.py` - DynamoDB score repository
- [ ] `eventbridge/eventbridge_publisher.py` - EventBridge publisher
- [ ] `ai/bedrock_generator.py` - Bedrock AI prompt generator
- [ ] `ai/prompt_cache.py` - Prompt caching (60s TTL)
- [ ] `replay/xml_parser.py` - XML parser (reuse conversion logic)
- [ ] `replay/replay_engine.py` - Replay engine with configurable speed
- [ ] `s3/replay_loader.py` - S3 replay data loader

#### Tests
- [ ] `tests/integration/` - Integration tests with moto

---

## Phase 5: Lambda Handlers 🔜 UPCOMING

### To Build

#### WebSocket Handlers (`src/interfaces/websocket_handlers/`)
- [ ] `connect.py` - Handle WebSocket connection (JWT validation)
- [ ] `disconnect.py` - Handle WebSocket disconnection
- [ ] `default.py` - Route incoming messages by type

#### Event Handlers (`src/interfaces/event_handlers/`)
- [ ] `replay_event.py` - EventBridge → match event consumer
- [ ] `game_engine_tick.py` - Scheduled prediction window opener
- [ ] `room_merger.py` - Scheduled inactive room merger

#### Composition Root
- [ ] `src/main.py` - Wire ports to adapters (cold-start optimization)

---

## Phase 6: Local Development 🔜 UPCOMING

### To Build

- [ ] `scripts/run_local_replay.py` - Run replay engine without AWS
  - Streams events to stdout
  - Configurable speed
  - No AWS dependencies

---

## Architecture Compliance

### Hexagonal Boundaries ✅
- Domain layer: Pure Python, zero AWS imports
- Application layer: Orchestrates domain + ports, zero AWS imports
- Infrastructure layer: AWS adapters only
- Interfaces layer: Thin Lambda handlers

### Type Safety ✅
- Type hints mandatory everywhere
- mypy --strict compliance target

### Testing Strategy ✅
- Unit tests: Domain + Application (fake ports)
- Integration tests: Infrastructure (moto mocks)
- Local dev: End-to-end without AWS

---

## Next Steps

1. **Install dependencies**: `make install`
2. **Start Phase 2**: Build domain entities and services
3. **Maintain test coverage**: Write tests alongside implementation
4. **Follow hexagonal boundaries**: Keep AWS out of domain/application layers

---

## Notes

- No Terraform in this repo (lives in InfraBudes)
- No frontend code (lives in FrontendBudes)
- WebSocket contract must match frontend exactly
- Cost control: Bedrock called max once per prediction window
- Prompt cache hit rate target: ≥60%
