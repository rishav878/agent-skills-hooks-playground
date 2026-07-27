from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    AgentRun,
    ApprovalRequest,
    ConversationMemory,
    Document,
    ExecutionEvent,
)


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_run(
        self, run_id: str, trace_id: str, input_data: str
    ) -> AgentRun:
        run = AgentRun(
            id=run_id,
            trace_id=trace_id,
            input=input_data,
            status="pending",
        )
        self._session.add(run)
        await self._session.commit()
        await self._session.refresh(run)
        return run

    async def get_run(self, run_id: str) -> AgentRun | None:
        result = await self._session.execute(
            select(AgentRun).where(AgentRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def update_run_status(self, run_id: str, status: str) -> None:
        await self._session.execute(
            update(AgentRun)
            .where(AgentRun.id == run_id)
            .values(status=status, updated_at=datetime.now(UTC))
        )
        await self._session.commit()

    async def save_event(
        self,
        event_id: str,
        run_id: str,
        trace_id: str,
        event_type: str,
        component: str,
        status: str,
        input_data: str | None = None,
        output_data: str | None = None,
        error: str | None = None,
        metadata_: str | None = None,
        duration_ms: int | None = None,
    ) -> ExecutionEvent:
        event = ExecutionEvent(
            id=event_id,
            run_id=run_id,
            trace_id=trace_id,
            event_type=event_type,
            component=component,
            status=status,
            input=input_data,
            output=output_data,
            error=error,
            metadata_=metadata_,
            duration_ms=duration_ms,
        )
        self._session.add(event)
        await self._session.commit()
        return event

    async def get_events_by_run(
        self, run_id: str, limit: int = 100, offset: int = 0
    ) -> list[ExecutionEvent]:
        result = await self._session.execute(
            select(ExecutionEvent)
            .where(ExecutionEvent.run_id == run_id)
            .order_by(ExecutionEvent.timestamp.asc())
            .offset(offset)
            .limit(limit)
        )
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
        approval = ApprovalRequest(
            id=approval_id,
            run_id=run_id,
            skill_name=skill_name,
            input_summary=input_summary,
            asker=asker,
            reason=reason,
            state_snapshot=state_snapshot,
            status="pending",
        )
        self._session.add(approval)
        await self._session.commit()
        return approval

    async def approve_request(self, approval_id: str) -> ApprovalRequest | None:
        result = await self._session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if approval is None:
            return None
        approval.status = "approved"
        approval.decided_at = datetime.now(UTC)
        await self._session.commit()
        return approval

    async def get_approval_by_run(self, run_id: str) -> ApprovalRequest | None:
        result = await self._session.execute(
            select(ApprovalRequest)
            .where(ApprovalRequest.run_id == run_id)
            .order_by(ApprovalRequest.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def deny_request(self, approval_id: str) -> ApprovalRequest | None:
        result = await self._session.execute(
            select(ApprovalRequest).where(ApprovalRequest.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if approval is None:
            return None
        approval.status = "denied"
        approval.decided_at = datetime.now(UTC)
        await self._session.commit()
        return approval

    async def update_run(
        self, run_id: str, status: str, output: str | None = None
    ) -> None:
        values: dict = {"status": status, "updated_at": datetime.now(UTC)}
        if output is not None:
            values["output"] = output
        await self._session.execute(
            update(AgentRun).where(AgentRun.id == run_id).values(**values)
        )
        await self._session.commit()

    async def save_memory(
        self,
        memory_id: str,
        run_id: str,
        trace_id: str,
        skill_name: str,
        task: str,
        summary: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> ConversationMemory:
        mem = ConversationMemory(
            id=memory_id,
            run_id=run_id,
            trace_id=trace_id,
            skill_name=skill_name,
            task=task,
            summary=summary,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self._session.add(mem)
        await self._session.commit()
        return mem

    async def get_memories_by_skill(
        self, skill_name: str, limit: int = 20
    ) -> list[ConversationMemory]:
        result = await self._session.execute(
            select(ConversationMemory)
            .where(ConversationMemory.skill_name == skill_name)
            .order_by(ConversationMemory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        source: str | None = None,
        skill_name: str | None = None,
        metadata_: str | None = None,
    ) -> Document:
        doc = Document(
            id=doc_id,
            title=title,
            content=content,
            source=source,
            skill_name=skill_name,
            metadata_=metadata_,
        )
        self._session.add(doc)
        await self._session.commit()
        return doc

    async def get_document(self, doc_id: str) -> Document | None:
        result = await self._session.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def list_documents(
        self, skill_name: str | None = None, limit: int = 50, offset: int = 0
    ) -> list[Document]:
        stmt = select(Document).order_by(Document.created_at.desc())
        if skill_name:
            stmt = stmt.where(Document.skill_name == skill_name)
        stmt = stmt.offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_document(self, doc_id: str) -> bool:
        result = await self._session.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            return False
        await self._session.delete(doc)
        await self._session.commit()
        return True

    async def update_document_embedding(self, doc_id: str) -> None:
        await self._session.execute(
            update(Document)
            .where(Document.id == doc_id)
            .values(embedding_updated=True)
        )
        await self._session.commit()
