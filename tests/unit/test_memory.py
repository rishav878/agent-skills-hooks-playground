import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base
from app.database.repository import Repository
from app.memory.service import MemoryService


@pytest_asyncio.fixture
async def service() -> MemoryService:
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()
    repo = Repository(session)
    return MemoryService(repo)


class TestMemoryService:
    @pytest.mark.asyncio
    async def test_save_and_get_memories(self, service: MemoryService) -> None:
        run_id = str(uuid.uuid4())
        saved = await service.save_conversation(
            run_id=run_id,
            trace_id=str(uuid.uuid4()),
            skill_name="research",
            task="research AI",
            summary="Found useful info about AI",
        )
        assert saved["skill_name"] == "research"
        assert saved["task"] == "research AI"

        memories = await service.get_memories_by_skill("research", limit=10)
        assert len(memories) >= 1
        assert memories[0]["run_id"] == run_id

    @pytest.mark.asyncio
    async def test_get_memories_empty(self, service: MemoryService) -> None:
        memories = await service.get_memories_by_skill("nonexistent", limit=10)
        assert memories == []

    @pytest.mark.asyncio
    async def test_get_recent_context(self, service: MemoryService) -> None:
        await service.save_conversation(
            run_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            skill_name="code_review",
            task="review main.py",
            summary="Found 3 bugs",
        )
        context = await service.get_recent_context("code_review", top_k=3)
        assert "review main.py" in context
        assert "Found 3 bugs" in context

    @pytest.mark.asyncio
    async def test_get_recent_context_empty(self, service: MemoryService) -> None:
        context = await service.get_recent_context("nonexistent", top_k=3)
        assert context == ""

    @pytest.mark.asyncio
    async def test_multiple_skills_isolation(self, service: MemoryService) -> None:
        await service.save_conversation(
            run_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            skill_name="research",
            task="research topic",
        )
        await service.save_conversation(
            run_id=str(uuid.uuid4()),
            trace_id=str(uuid.uuid4()),
            skill_name="code_review",
            task="review code",
        )
        r_mem = await service.get_memories_by_skill("research", limit=10)
        c_mem = await service.get_memories_by_skill("code_review", limit=10)
        assert len(r_mem) == 1
        assert len(c_mem) == 1
