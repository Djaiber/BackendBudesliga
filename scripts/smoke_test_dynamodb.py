#!/usr/bin/env python3
"""Smoke test: DynamoDB room + score + window repositories against real AWS.

Usage:
    AWS_REGION=eu-central-1 DYNAMODB_TABLE=budes-dev python scripts/smoke_test_dynamodb.py

NOT run by pytest. Manual execution only.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.infrastructure.dynamodb.room_repository_ddb import RoomRepositoryDDB
from src.infrastructure.dynamodb.score_repository_ddb import ScoreRepositoryDDB

TABLE = os.environ["DYNAMODB_TABLE"]
REGION = os.environ.get("AWS_REGION", "eu-central-1")


async def smoke_dynamodb() -> None:
    from src.domain.entities import Player, Room

    rooms = RoomRepositoryDDB(table_name=TABLE, region=REGION)
    scores = ScoreRepositoryDDB(table_name=TABLE, region=REGION)

    room_id = "SMOKE-ROOM-001"
    user_id = "smoke-user-001"

    print(f"[DynamoDB] table={TABLE} region={REGION}")

    # --- Room save / get ---
    room = Room(
        room_id=room_id,
        status="OPEN",
        players=[],
        created_at_ms=1_000_000,
        match_id="match-smoke",
    )
    await rooms.save(room)
    print("  ✓ room saved")

    fetched = await rooms.get(room_id)
    assert fetched is not None and fetched.room_id == room_id, "room get failed"
    print("  ✓ room retrieved")

    # --- Score upsert / get ---
    player = Player(user_id=user_id, display_name="Smoke User", score=0, tier="ENTHUSIAST", streak=0)
    await scores.upsert_player(room_id=room_id, player=player)
    print("  ✓ score upserted")

    fetched_player = await scores.get_player(room_id=room_id, user_id=user_id)
    assert fetched_player is not None, "score get failed"
    print("  ✓ score retrieved")

    # --- Leaderboard ---
    lb = await scores.leaderboard(room_id=room_id, limit=5)
    assert len(lb) >= 1, "leaderboard empty"
    print(f"  ✓ leaderboard has {len(lb)} entries")

    # --- Cleanup ---
    await rooms.delete(room_id)
    print("  ✓ room deleted")

    print("[DynamoDB] PASS")


if __name__ == "__main__":
    asyncio.run(smoke_dynamodb())
