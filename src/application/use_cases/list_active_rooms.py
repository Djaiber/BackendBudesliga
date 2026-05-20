"""List active rooms use case."""

from ...domain.entities import Room
from ...domain.ports import RoomRepository


class ListActiveRoomsUseCase:
    """Thin wrapper around RoomRepository.list_by_status('active')."""

    def __init__(self, room_repo: RoomRepository) -> None:
        self._room_repo = room_repo

    async def execute(self) -> list[Room]:
        return await self._room_repo.list_by_status("active")
