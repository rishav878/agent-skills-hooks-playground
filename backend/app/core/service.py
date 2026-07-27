import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.events import AgentEvent
from app.core.publisher import EventPublisher, get_publisher
from app.core.redaction import SecretRedactor
from app.core.redaction import redactor as default_redactor
from app.database.models import AgentRun, ApprovalRequest
from app.database.repository import Repository

logger = logging.getLogger(__name__)


class EventService:
    def __init__(
        self,
        session: AsyncSession,
        publisher: EventPublisher | None = None,
        redactor: SecretRedactor | None = None,
    ) -> None:
        self._session = session
        self._repo = Repository(session)
        self._publisher = publisher or get_publisher()
        self._redactor = redactor or default_redactor

    async def save_and_publish(self, event: AgentEvent) -> None:
        redacted_input = self._redactor.redact(event.input)
        redacted_output = self._redactor.redact(event.output)
        redacted_metadata = self._redactor.redact(event.metadata)

        await self._repo.save_event(
            event_id=event.event_id,
            run_id=event.run_id,
            trace_id=event.trace_id,
            event_type=event.event_type.value,
            component=event.component.value,
            status=event.status.value,
            input_data=json.dumps(redacted_input) if redacted_input else None,
            output_data=json.dumps(redacted_output) if redacted_output else None,
            error=json.dumps(event.error) if event.error else None,
            metadata_=json.dumps(redacted_metadata) if redacted_metadata else None,
            duration_ms=event.duration_ms,
        )

        redacted = event.model_copy(update={
            "input": redacted_input,
            "output": redacted_output,
            "metadata": redacted_metadata,
        })
        await self._publisher.publish(redacted)

    async def create_run(
        self, run_id: str, trace_id: str, input_data: str
    ) -> AgentRun:
        return await self._repo.create_run(run_id, trace_id, input_data)

    async def get_run(self, run_id: str) -> AgentRun | None:
        return await self._repo.get_run(run_id)

    async def update_run_status(self, run_id: str, status: str) -> None:
        await self._repo.update_run_status(run_id, status)

    async def get_events_by_run(
        self, run_id: str, limit: int = 100, offset: int = 0
    ) -> list[Any]:
        return await self._repo.get_events_by_run(run_id, limit, offset)

    async def get_all_runs(
        self, limit: int = 50, offset: int = 0
    ) -> list[AgentRun]:
        stmt = (
            select(AgentRun)
            .order_by(AgentRun.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def create_approval(
        self,
        approval_id: str,
        run_id: str,
        skill_name: str,
        input_summary: str,
        asker: str,
        reason: str | None,
        state_snapshot: str,
    ) -> ApprovalRequest:
        return await self._repo.create_approval(
            approval_id, run_id, skill_name, input_summary, asker, reason, state_snapshot
        )

    async def get_pending_approval(self, run_id: str) -> ApprovalRequest | None:
        approval = await self._repo.get_approval_by_run(run_id)
        if approval is not None and approval.status == "pending":
            return approval
        return None

    async def approve_request(self, approval_id: str) -> ApprovalRequest | None:
        return await self._repo.approve_request(approval_id)

    async def deny_request(self, approval_id: str) -> ApprovalRequest | None:
        return await self._repo.deny_request(approval_id)

    async def update_run(
        self, run_id: str, status: str, output: str | None = None
    ) -> None:
        await self._repo.update_run(run_id, status, output)
