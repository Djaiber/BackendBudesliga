"""Fake implementations of domain ports for testing."""

from .fake_ai_generator import FakeAIGenerator
from .fake_clock import FakeClock
from .fake_event_publisher import FakeEventPublisher
from .fake_id_generator import FakeIdGenerator
from .fake_room_repository import FakeRoomRepository
from .fake_score_repository import FakeScoreRepository
from .fake_websocket_broadcaster import FakeWebSocketBroadcaster
from .fake_window_repository import FakeWindowRepository

__all__ = [
    "FakeAIGenerator",
    "FakeClock",
    "FakeEventPublisher",
    "FakeIdGenerator",
    "FakeRoomRepository",
    "FakeScoreRepository",
    "FakeWebSocketBroadcaster",
    "FakeWindowRepository",
]
