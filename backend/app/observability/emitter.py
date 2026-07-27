from typing import Protocol

from app.core.events import AgentEvent


class EventEmitter(Protocol):
    async def emit(self, event: AgentEvent) -> None: ...
