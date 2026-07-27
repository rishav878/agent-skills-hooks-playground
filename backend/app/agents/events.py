import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.events import AgentEvent, Component, EventType, Status
from app.core.service import EventService


class EventEmitter:
    def __init__(self, service: EventService | None = None) -> None:
        self._service = service
        self.events: list[AgentEvent] = []

    def with_service(self, service: EventService) -> "EventEmitter":
        self._service = service
        return self

    async def emit(self, event: AgentEvent) -> None:
        self.events.append(event)

        if self._service is not None:
            try:
                await self._service.save_and_publish(event)
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "Failed to persist event %s", event.event_id
                )

    async def emit_event(
        self,
        run_id: str,
        trace_id: str,
        event_type: EventType,
        component: Component,
        status: Status,
        input: dict | None = None,
        output: dict | None = None,
        error: dict | None = None,
        metadata: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> AgentEvent:
        event = AgentEvent(
            event_id=str(uuid.uuid4()),
            run_id=run_id,
            trace_id=trace_id,
            timestamp=datetime.now(UTC),
            event_type=event_type,
            component=component,
            status=status,
            duration_ms=duration_ms,
            input=input,
            output=output,
            error=error,
            metadata=metadata or {},
        )
        await self.emit(event)
        return event
