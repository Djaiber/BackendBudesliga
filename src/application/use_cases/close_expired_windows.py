"""Close expired prediction windows use case."""

from ...domain.ports import Clock, WindowRepository
from .close_prediction_window import ClosePredictionWindowUseCase


class CloseExpiredWindowsUseCase:
    """Close all expired-but-still-open prediction windows for a room.

    Returns the list of window IDs that were closed.
    """

    def __init__(
        self,
        window_repo: WindowRepository,
        close_window: ClosePredictionWindowUseCase,
        clock: Clock,
    ) -> None:
        self._window_repo = window_repo
        self._close_window = close_window
        self._clock = clock

    async def execute(self, room_id: str) -> list[str]:
        open_windows = await self._window_repo.list_open_by_room(room_id)
        now_ms = self._clock.now_ms()
        closed: list[str] = []

        for window in open_windows:
            if window.is_expired(now_ms):
                await self._close_window.execute(window.window_id)
                closed.append(window.window_id)

        return closed
