# Phase 2 Complete: Domain Layer ✅

## Summary

Phase 2 of the BackendBudes project is **complete**. The domain layer has been built with pure Python, zero AWS dependencies, and full unit test coverage.

## What Was Built

### 1. Domain Entities (6 entities)

All entities are **immutable** (`@dataclass(frozen=True)`) with validation in `__post_init__`:

- **MatchEvent** - Match events with minute/second validation (0-120, 0-59)
- **Player** - Player with score, tier, streak (all >= 0)
- **Room** - Room with 0-4 players, status validation, `is_mergeable()` helper
- **PredictionWindow** - Time-limited mini-game with `is_expired()` helper
- **Prediction** - Player's submitted prediction (string or int value)
- **ScoreDelta** - Result of scoring calculation with multipliers

### 2. Domain Services (5 services)

All services are **pure functions** - same inputs always produce same outputs:

- **TierService** - Calculate tier from EXP (0-400 Dummies, 401-700 Enthusiast, 701-900 Amateur, 901+ Savvy)
- **StreakService** - Track streaks (correct→+1, wrong→0) and multipliers (3→1.2x, 5→1.5x)
- **ScoringService** - Calculate points with speed multiplier (1.0-1.1 linear) and streak multiplier stacking
- **MatchmakerService** - Find mergeable rooms (<3 players, combined ≤4), check if room can accept players
- **GameEngineService** - Select mini-game based on recent events, resolve predictions and rank players

### 3. Domain Ports (5 protocols)

All ports use **Protocol** (structural typing) with **async** methods:

- **RoomRepository** - get, save, list_by_status, add_player, remove_player, delete
- **ScoreRepository** - get_player, upsert_player, apply_delta, leaderboard
- **EventPublisher** - publish domain events
- **AIGenerator** - generate_prompt for mini-games
- **WebSocketBroadcaster** - send_to_connection, broadcast_to_room

### 4. Unit Tests (98 tests)

**100% coverage on entities, 97-100% on services**

#### Entity Tests (33 tests)
- Happy path for each entity
- Validation tests for each constraint
- Immutability tests (frozen dataclass)

#### Service Tests (65 tests)
- **TierService**: 15 tests (all boundaries + negative input)
- **StreakService**: 10 tests (increment, reset, all multiplier thresholds)
- **ScoringService**: 16 tests (all ranks, speed multiplier, streak stacking, penalties)
- **MatchmakerService**: 10 tests (pairing logic, can_join conditions)
- **GameEngineService**: 15 tests (game selection, all resolution types, ties, invalid inputs)

## Test Results

```bash
# Run all tests
./venv/bin/pytest tests/unit/ -v
# ✅ 98 passed in 0.16s

# Check coverage
./venv/bin/pytest tests/unit/ --cov=src.domain --cov-report=term
# Entities: 100%
# Services: 97-100%
# Total: 93% (ports are interfaces, not tested)

# Type checking
./venv/bin/mypy src/domain/ --strict --explicit-package-bases
# ✅ Success: no issues found in 20 source files

# Linting
./venv/bin/ruff check src/domain/ tests/unit/
# ✅ All checks passed!
```

## Architecture Compliance ✅

### Hexagonal Boundaries Enforced

- ✅ **Zero AWS imports** in domain layer
- ✅ **Zero I/O** - all services are pure, synchronous functions
- ✅ **Zero time.time()** - callers pass `now_ms` explicitly for determinism
- ✅ **Zero uuid.uuid4()** - callers pass IDs in
- ✅ **Ports are async** (Protocols) - adapters will be async
- ✅ **Domain is sync** - pure business logic

### Type Safety

- ✅ **mypy --strict** passes on all domain code
- ✅ **Type hints** on every function and method
- ✅ **Immutable entities** (frozen dataclasses)
- ✅ **Structural typing** (Protocol) for ports

### Testability

- ✅ **100% unit testable** - no mocks needed
- ✅ **Deterministic** - same inputs → same outputs
- ✅ **Fast** - 98 tests run in 0.16 seconds
- ✅ **Isolated** - no external dependencies

## Key Design Decisions

### 1. Immutable Entities
All entities are frozen dataclasses. This ensures:
- Thread safety
- Predictable behavior
- Easy testing
- No accidental mutations

### 2. Pure Services
All services are stateless with pure methods:
- No side effects
- Deterministic output
- Easy to test
- Easy to reason about

### 3. Protocols for Ports
Using `typing.Protocol` instead of ABC:
- Structural typing (duck typing with type safety)
- No inheritance required
- More flexible for adapters
- Better for testing with fakes

### 4. Validation at Entity Boundaries
Entities validate themselves in `__post_init__`:
- Invalid states are impossible
- Fail fast at construction
- Services can trust entity invariants
- Reduces defensive programming

## Domain Rules Implemented

### Scoring Rules ✅
- Exact prediction: 100 points
- Closest non-exact: 50, 30, 20, 10 (ranks 2-5)
- No response: -10 penalty
- Speed multiplier: 1.0 at deadline, 1.1 at open (linear)
- Multipliers never apply to penalties

### Streak Rules ✅
- Correct prediction: increment streak
- Wrong prediction: reset to 0
- 3+ correct: 1.2x multiplier
- 5+ correct: 1.5x multiplier
- Streak multiplier stacks with speed multiplier

### Tier Rules ✅
- Dummies: 0-400 EXP
- Enthusiast: 401-700 EXP
- Amateur: 701-900 EXP
- Savvy: 901+ EXP (capped)

### Room Rules ✅
- 0-4 players per room
- Rooms with <3 players are mergeable
- Merged rooms cannot exceed 4 players
- Only active rooms can be joined or merged

### Game Selection Rules ✅
- Recent corners → CORNERS_IN_INTERVAL
- Recent shots (no corners) → GOAL_IN_TIME_WINDOW
- Otherwise → NEXT_GOAL_TIMING
- Deterministic (same events → same game)

## File Structure

```
src/domain/
├── __init__.py
├── entities/
│   ├── __init__.py
│   ├── match_event.py
│   ├── player.py
│   ├── prediction.py
│   ├── prediction_window.py
│   ├── room.py
│   └── score.py
├── services/
│   ├── __init__.py
│   ├── game_engine_service.py
│   ├── matchmaker_service.py
│   ├── scoring_service.py
│   ├── streak_service.py
│   └── tier_service.py
└── ports/
    ├── __init__.py
    ├── ai_generator.py
    ├── event_publisher.py
    ├── room_repository.py
    ├── score_repository.py
    └── websocket_broadcaster.py

tests/unit/
├── __init__.py
├── entities/
│   ├── __init__.py
│   ├── test_match_event.py (7 tests)
│   ├── test_player.py (5 tests)
│   ├── test_prediction.py (3 tests)
│   ├── test_prediction_window.py (8 tests)
│   ├── test_room.py (7 tests)
│   └── test_score.py (3 tests)
└── services/
    ├── __init__.py
    ├── test_game_engine_service.py (15 tests)
    ├── test_matchmaker_service.py (10 tests)
    ├── test_scoring_service.py (16 tests)
    ├── test_streak_service.py (10 tests)
    └── test_tier_service.py (14 tests)
```

## Next Steps: Phase 3

Phase 3 will build the **Application Layer** (use cases):

1. **Use Cases** - Orchestrate domain services with ports
   - `join_room.py`
   - `submit_prediction.py`
   - `open_prediction_window.py`
   - `close_prediction_window.py`
   - `handle_match_event.py`
   - `broadcast_emoji.py`
   - `merge_inactive_rooms.py`

2. **DTOs** - Request/response message shapes
   - `messages.py`

3. **Tests** - Use cases with fake port implementations

The application layer will:
- Have zero AWS imports (like domain)
- Inject ports via constructor
- Orchestrate domain services
- Be fully unit testable with fakes

## Verification Commands

Run these commands to verify Phase 2 completion:

```bash
# Install dependencies
make install

# Run all tests
make test
# Expected: 98 passed

# Type check
make typecheck
# Expected: Success: no issues found

# Lint
make lint
# Expected: All checks passed!

# Check service coverage
pytest tests/unit/services/ --cov=src.domain.services --cov-report=term
# Expected: 97-100% coverage
```

## Success Criteria ✅

All Phase 2 acceptance criteria met:

- ✅ All entities as frozen dataclasses with validation
- ✅ All services as pure functions (no I/O, no AWS)
- ✅ All ports as async Protocols
- ✅ 98 unit tests, all passing
- ✅ 100% coverage on entities
- ✅ 97-100% coverage on services
- ✅ mypy --strict passes
- ✅ ruff passes with zero warnings
- ✅ Zero AWS imports in domain/
- ✅ Zero time.time() or uuid.uuid4() in services

**Phase 2 is production-ready and fully validated.**
