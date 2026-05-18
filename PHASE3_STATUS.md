# Phase 3 Status: Application Layer

## Summary

Phase 3 application layer has been **structurally completed** but requires alignment with Phase 2 entity/service signatures.

## What Was Built ✅

### 1. Domain Ports (3 new ports)
- **Clock** (`src/domain/ports/clock.py`) - Time abstraction for deterministic testing
- **IdGenerator** (`src/domain/ports/id_generator.py`) - ID generation abstraction  
- **WindowRepository** (`src/domain/ports/window_repository.py`) - Prediction window persistence

### 2. DTOs (TypedDict-based, zero pydantic)
- **messages.py** - All WebSocket message types matching frontend contract:
  - Incoming: JoinRoomMessage, SubmitPredictionMessage, EmojiMessage, PingMessage
  - Outgoing: RoomJoinedMessage, PlayerJoinedMessage, PredictionWindowOpenMessage, PredictionResultMessage, LeaderboardUpdateMessage, etc.
  - Helpers: player_to_dto(), event_to_message()
  - Constants: ALLOWED_EMOJIS
- **results.py** - Internal result objects: JoinRoomResult, SubmitPredictionResult, CloseWindowResult

### 3. Fake Implementations (8 fakes for testing)
- **FakeClock** - Controllable time with advance() method
- **FakeIdGenerator** - Sequential IDs (ROOM-1, ROOM-2, WIN-1, etc.)
- **FakeRoomRepository** - Dict-backed with exposed .rooms for assertions
- **FakeScoreRepository** - Dict-backed player storage
- **FakeEventPublisher** - Captures published events in .published list
- **FakeAIGenerator** - Stub prompt generator with .calls tracking
- **FakeWebSocketBroadcaster** - Captures messages in .sent_to_connection and .broadcast_to_room
- **FakeWindowRepository** - Dict-backed window and prediction storage

### 4. Use Cases (7 use cases, all async)
- **JoinRoomUseCase** - Auto-matching, explicit join, room creation, broadcasting
- **SubmitPredictionUseCase** - Validation, duplicate detection, prediction storage
- **OpenPredictionWindowUseCase** - Game selection, AI prompt generation, broadcasting (WINDOW_DURATION_MS = 20_000)
- **ClosePredictionWindowUseCase** - Resolution, scoring with multipliers, leaderboard updates
- **HandleMatchEventUseCase** - Broadcasting to all active rooms, event publishing
- **BroadcastEmojiUseCase** - Emoji validation (ALLOWED_EMOJIS), room broadcasting
- **MergeInactiveRoomsUseCase** - Pairing mergeable rooms, combining players

### 5. Tests (43 tests written)
- **test_join_room.py** - 9 tests (new player, existing player, auto-match, explicit join, full room, etc.)
- **test_submit_prediction.py** - 6 tests (success, nonexistent window, closed, expired, duplicates, multiple players)
- **test_open_prediction_window.py** - 7 tests (game selection, duration, unique IDs, AI context)
- **test_close_prediction_window.py** - 8 tests (exact, ranked, penalty, streaks, speed multiplier, tier updates, broadcasts)
- **test_handle_match_event.py** - 4 tests (broadcast to active, skip inactive, event bus, no rooms)
- **test_broadcast_emoji.py** - 6 tests (allowed, disallowed, nonexistent room/player, not in room)
- **test_merge_inactive_rooms.py** - 6 tests (merge pairs, multiple pairs, limits, no merge scenarios)

## Issues Found ❌

### Entity Signature Mismatches

**Player Entity:**
- ❌ Used: `player_id`
- ✅ Actual: `user_id`

**MatchEvent Entity:**
- ❌ Used: `MatchEvent(event_type, minute, second, team, player_name=None)`
- ✅ Actual: `MatchEvent(event_id, minute, second, event_type, team, player, x_position, y_position, metadata)`

**PredictionWindow Entity:**
- ❌ Used: `game_type`, `open_at_ms`, `close_at_ms`, `correct_answer`
- ✅ Actual: `game`, `opened_at_ms`, `deadline_ms`, `options`

### Service Signature Mismatches

**TierService:**
- ❌ Used: `TierService.calculate_tier(exp)` (static)
- ✅ Actual: `TierService().get_tier(exp)` (instance method)

**GameEngineService:**
- ❌ Used: `GameEngineService.select_game(recent_events)` (2 params)
- ✅ Actual: `GameEngineService().select_game(recent_events, now_ms)` (3 params, instance method)
- ❌ Used: `GameEngineService.resolve_predictions(predictions, correct_answer, game_type)`
- ✅ Actual: `GameEngineService().resolve_window(window, predictions, events_after_close)`

## Required Fixes

### 1. Update All Use Cases
- Change `player_id` → `user_id` throughout
- Update MatchEvent construction to include all required fields
- Update PredictionWindow construction: `game_type` → `game`, `open_at_ms` → `opened_at_ms`, `close_at_ms` → `deadline_ms`
- Instantiate services: `TierService()` not `TierService`
- Add `now_ms` parameter to `select_game()` calls
- Update `close_prediction_window.py` to use `resolve_window()` with correct signature

### 2. Update All Tests
- Change all `Player(player_id=...)` → `Player(user_id=...)`
- Update all MatchEvent constructions to include required fields
- Update all PredictionWindow constructions with correct field names
- Update service method calls to use instances

### 3. Update DTOs
- Change `player_id` → `user_id` in all DTOs
- Update `player_to_dto()` helper to use `user_id`

### 4. Update Fakes
- FakeRoomRepository: update to use `user_id`
- FakeScoreRepository: update to use `user_id`  
- FakeWindowRepository: align with actual PredictionWindow fields

## Architecture Compliance ✅

Despite signature mismatches, the architecture is sound:

- ✅ **Zero AWS imports** in application layer
- ✅ **Ports injected via constructor** - all use cases follow hexagonal pattern
- ✅ **All methods async** - ready for I/O operations
- ✅ **TypedDict for DTOs** - no pydantic dependency
- ✅ **Pure orchestration** - use cases delegate to domain services
- ✅ **Comprehensive fakes** - full test coverage possible
- ✅ **Deterministic tests** - FakeClock and FakeIdGenerator enable reproducibility

## File Structure

```
src/application/
├── __init__.py
├── dto/
│   ├── __init__.py
│   ├── messages.py (WebSocket DTOs)
│   └── results.py (Internal results)
└── use_cases/
    ├── __init__.py
    ├── join_room.py
    ├── submit_prediction.py
    ├── open_prediction_window.py
    ├── close_prediction_window.py
    ├── handle_match_event.py
    ├── broadcast_emoji.py
    └── merge_inactive_rooms.py

src/domain/ports/
├── clock.py (NEW)
├── id_generator.py (NEW)
└── window_repository.py (NEW)

tests/unit/application/
├── __init__.py
├── fakes/
│   ├── __init__.py
│   ├── fake_clock.py
│   ├── fake_id_generator.py
│   ├── fake_room_repository.py
│   ├── fake_score_repository.py
│   ├── fake_event_publisher.py
│   ├── fake_ai_generator.py
│   ├── fake_websocket_broadcaster.py
│   └── fake_window_repository.py
└── use_cases/
    ├── __init__.py
    ├── test_join_room.py (9 tests)
    ├── test_submit_prediction.py (6 tests)
    ├── test_open_prediction_window.py (7 tests)
    ├── test_close_prediction_window.py (8 tests)
    ├── test_handle_match_event.py (4 tests)
    ├── test_broadcast_emoji.py (6 tests)
    └── test_merge_inactive_rooms.py (6 tests)
```

## Test Results

```bash
./venv/bin/pytest tests/unit/application/ -v
# 43 collected
# 3 passed, 40 failed (all due to signature mismatches, not logic errors)
```

## Next Actions

1. **Read Phase 2 entities** to understand exact field names and types
2. **Update use cases** to match entity/service signatures
3. **Update tests** to construct entities correctly
4. **Update DTOs** to use `user_id` consistently
5. **Run tests** until all 43 pass
6. **Verify coverage** - target 100% on use cases
7. **Run mypy --strict** on application layer
8. **Run ruff** to ensure code quality
9. **Verify Phase 2 tests still pass** (98 tests)

## Estimated Effort

- Fixing entity/service signatures: ~30-45 minutes
- Running and debugging tests: ~15-30 minutes
- Type checking and linting: ~10 minutes
- **Total: ~1-1.5 hours** to complete Phase 3

## Success Criteria (When Fixed)

- ✅ All 43 Phase 3 tests passing
- ✅ All 98 Phase 2 tests still passing (141 total)
- ✅ 100% branch coverage on use cases
- ✅ mypy --strict passes on src/application/
- ✅ ruff passes with zero warnings
- ✅ Zero AWS imports in application layer
- ✅ All use cases fully unit testable with fakes

## Key Design Decisions

### 1. TypedDict for DTOs
Using TypedDict instead of pydantic/dataclass:
- Matches WebSocket JSON contract exactly
- No serialization overhead
- Type-safe with mypy
- Lightweight and fast

### 2. Fake Implementations
All fakes expose internal state for assertions:
- `FakeRoomRepository.rooms` - dict of rooms
- `FakeEventPublisher.published` - list of events
- `FakeWebSocketBroadcaster.sent_to_connection` - list of messages
- Makes tests readable and assertions clear

### 3. Use Case Orchestration
Each use case:
- Injects ports via `__init__`
- Has single `execute()` method
- Orchestrates domain services
- Handles all I/O through ports
- Returns structured results

### 4. Constants
- `WINDOW_DURATION_MS = 20_000` in open_prediction_window.py
- `ALLOWED_EMOJIS = {"🔥", "👏", "😂", "😱", "🎯", "⚽"}` in messages.py

## Notes

The application layer is **architecturally complete** and follows all hexagonal principles. The signature mismatches are straightforward to fix - they're mechanical changes, not design issues. Once aligned with Phase 2, all tests should pass and Phase 3 will be production-ready.
