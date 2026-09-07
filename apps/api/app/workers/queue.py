"""Job queue abstraction."""

from typing import Any, Protocol


class JobQueue(Protocol):
    async def enqueue_pipeline(self, check_id: str, check_type: str, input_data: dict[str, Any]) -> None:
        ...
