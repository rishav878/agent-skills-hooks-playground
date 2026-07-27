import json
import uuid
from datetime import UTC, datetime

from app.core.events import AgentEvent, EventType, Status
from app.core.redaction import redactor
from app.database.repository import Repository


class DatabaseEventEmitter:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    async def emit(self, event: AgentEvent) -> None:
        await self._repository.save_event(
            event_id=event.event_id,
            run_id=event.run_id,
            trace_id=event.trace_id,
            event_type=event.event_type.value,
            component=event.component.value,
            status=event.status.value,
            input_data=json.dumps(redactor.redact(event.input))
            if event.input
            else None,
            output_data=json.dumps(redactor.redact(event.output))
            if event.output
            else None,
            error=json.dumps(event.error) if event.error else None,
            metadata_=json.dumps(event.metadata) if event.metadata else None,
            duration_ms=event.duration_ms,
        )


def create_event(
    run_id: str,
    trace_id: str,
    event_type: EventType,
    status: Status,
    component: str = "system",
    input_data: dict | None = None,
    output_data: dict | None = None,
    error: dict | None = None,
    metadata_: dict | None = None,
    duration_ms: int | None = None,
) -> AgentEvent:
    return AgentEvent(
        event_id=str(uuid.uuid4()),
        run_id=run_id,
        trace_id=trace_id,
            timestamp=datetime.now(UTC),
        event_type=event_type,
        component=component,
        status=status,
        input=input_data,
        output=output_data,
        error=error,
        metadata=metadata_ or {},
        duration_ms=duration_ms,
    )
